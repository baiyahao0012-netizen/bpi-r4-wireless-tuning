#!/usr/bin/env python3
"""RTP media lab: rtpbin + RFC4588 RTX + jitterbuffer retransmission.

Two roles, run as two processes (local loopback or across a link).

  sender   file -> h264parse -> rtph264pay(96) -> rtpbin(s0)
           rtpbin send_rtp_src_0 -> [identity drop] -> udpsink 5004
           rtpbin send_rtcp_src_0 -> udpsink 5006
           udpsrc 5005 -> rtpbin recv_rtcp_sink_0
           request-aux-sender -> rtprtxsend (96->97)

  receiver udpsrc 5004 -> rtpbin recv_rtp_sink_0
           rtpbin send_rtcp_src_0 -> udpsink 5005
           udpsrc 5006 -> rtpbin recv_rtcp_sink_0
           request-aux-receiver -> rtprtxreceive (96->97)
           request-jitterbuffer -> do-retransmission
           recv_rtp_src_0 -> rtph264depay -> h264parse -> avdec_h264 -> fakesink

Prints one RESULT json line per role.
"""
import argparse
import json
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib  # noqa: E402

Gst.init(None)

PT_NAMES = {200: "SR", 201: "RR", 205: "NACK", 206: "PLI"}


def make(factory, name):
    el = Gst.ElementFactory.make(factory, name)
    if el is None:
        raise RuntimeError("missing element: %s" % factory)
    return el


def pt_map_structure():
    res = Gst.Structure.from_string("application/x-rtp-pt-map,96=(uint)97")
    for item in res:
        if isinstance(item, Gst.Structure):
            return item
    raise RuntimeError("cannot build payload-type-map: %r" % (res,))


def rtcp_pts(buf):
    out = []
    try:
        data = bytes(buf.extract_dup(0, buf.get_size()))
    except Exception:
        return out
    i = 0
    while i + 4 <= len(data):
        if (data[i] >> 6) != 2:
            break
        pt = data[i + 1]
        length = ((data[i + 2] << 8) | data[i + 3]) * 4 + 4
        out.append(pt)
        if length <= 0:
            break
        i += length
    return out


def probe_buffer(info):
    for name in ("get_buffer", "get_current_buffer"):
        fn = getattr(info, name, None)
        if fn is not None:
            try:
                buf = fn()
                if buf is not None:
                    return buf
            except Exception:
                pass
    try:
        data = info.data
        if isinstance(data, Gst.Buffer):
            return data
    except Exception:
        pass
    return None


def probe_rtcp(pad, stats, tag):
    def cb(pad_, info):
        buf = probe_buffer(info)
        if buf is not None:
            for pt in rtcp_pts(buf):
                key = "%s_%s" % (tag, PT_NAMES.get(pt, str(pt)))
                stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_count(pad, stats, key):
    def cb(pad_, info):
        stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def build_sender(a, stats):
    p = Gst.Pipeline.new("sender")
    rtpbin = make("rtpbin", "rtpbin")
    rtpbin.set_property("latency", 200)
    rtpbin.set_property("do-retransmission", True)
    try:
        rtpbin.set_property("rtp-profile", 3)  # AVPF（枚举：1=avp, 3=avpf）
    except Exception as exc:
        print("WARN rtp-profile: %s" % exc, flush=True)
    src = make("filesrc", "src")
    src.set_property("location", a.file)
    demux = make("qtdemux", "demux")
    parse = make("h264parse", "parse")
    pay = make("rtph264pay", "pay")
    pay.set_property("pt", 96)
    pay.set_property("config-interval", 1)
    drop = make("identity", "drop")
    drop.set_property("drop-probability", a.loss)
    q = make("queue", "q")
    rtp_sink = make("udpsink", "rtp_sink")
    rtp_sink.set_property("host", a.host)
    rtp_sink.set_property("port", a.rtp_port)
    rtp_sink.set_property("sync", False)
    rtp_sink.set_property("async", False)
    rtcp_sink = make("udpsink", "rtcp_sink")
    rtcp_sink.set_property("host", a.host)
    rtcp_sink.set_property("port", a.rtcp_port)
    rtcp_sink.set_property("sync", False)
    rtcp_sink.set_property("async", False)
    rtcp_src = make("udpsrc", "rtcp_src")
    rtcp_src.set_property("port", a.rtcp_feedback_port)
    rtcp_src.set_property("caps", Gst.Caps.from_string("application/x-rtcp"))
    rtxsend = make("rtprtxsend", "rtxsend")
    rtxsend.set_property("payload-type-map", pt_map_structure())

    # rtxsend 由 rtpbin 在 aux 信号回调中自行 add 并接线，不能提前加入管线
    for el in (src, demux, parse, pay, rtpbin, drop, q, rtp_sink, rtcp_sink, rtcp_src):
        p.add(el)

    src.link(demux)

    def demux_pad(bin_, pad):
        if pad.get_name().startswith("video"):
            pad.link(parse.get_static_pad("sink"))
    demux.connect("pad-added", demux_pad)
    parse.link(pay)

    def aux_sender(bin_, session):
        if session != 0:
            return None
        # Canonical form (server-rtpaux.c): wrap rtprtxsend in a bin exposing
        # ghost pads named src_%u / sink_%u; rtpbin expects that, not a raw element.
        b = Gst.Bin.new("rtxsend-bin")
        b.add(rtxsend)
        b.add_pad(Gst.GhostPad.new("src_0", rtxsend.get_static_pad("src")))
        b.add_pad(Gst.GhostPad.new("sink_0", rtxsend.get_static_pad("sink")))
        return b
    rtpbin.connect("request-aux-sender", aux_sender)

    def pad_added(bin_, pad):
        name = pad.get_name()
        if name.startswith("send_rtp_src_"):
            pad.link(drop.get_static_pad("sink"))
        elif name.startswith("send_rtcp_src_"):
            pad.link(rtcp_sink.get_static_pad("sink"))
            probe_rtcp(pad, stats, "out")
    rtpbin.connect("pad-added", pad_added)

    drop.link(q)
    q.link(rtp_sink)
    probe_count(drop.get_static_pad("src"), stats, "rtp_sent")
    fbpad = rtpbin.request_pad_simple("recv_rtcp_sink_0")
    rtcp_src.get_static_pad("src").link(fbpad)
    probe_count(rtcp_src.get_static_pad("src"), stats, "rtcp_in_raw")
    probe_rtcp(fbpad, stats, "in")
    stats["fbpad_is_linked"] = int(fbpad.is_linked())
    pay.get_static_pad("src").link(rtpbin.request_pad_simple("send_rtp_sink_0"))
    rtcp_out = rtpbin.request_pad_simple("send_rtcp_src_0")
    if rtcp_out is not None:
        ok = rtcp_out.link(rtcp_sink.get_static_pad("sink"))
        stats["rtcp_link_ok"] = int(bool(ok))
        stats["rtcp_is_linked"] = int(rtcp_out.is_linked())
        probe_rtcp(rtcp_out, stats, "out")
        probe_count(rtcp_sink.get_static_pad("sink"), stats, "rtcp_into_udpsink")
    else:
        stats["rtcp_link_ok"] = -1
    return p, rtxsend


def build_receiver(a, stats):
    p = Gst.Pipeline.new("receiver")
    rtpbin = make("rtpbin", "rtpbin")
    rtpbin.set_property("latency", a.latency)
    rtpbin.set_property("do-retransmission", not a.no_rtx)
    try:
        rtpbin.set_property("rtp-profile", 3)  # AVPF（枚举：1=avp, 3=avpf）
    except Exception as exc:
        print("WARN rtp-profile: %s" % exc, flush=True)
    rtp_src = make("udpsrc", "rtp_src")
    rtp_src.set_property("port", a.rtp_port)
    rtp_src.set_property("buffer-size", 8 * 1024 * 1024)
    rtp_src.set_property(
        "caps",
        Gst.Caps.from_string(
            "application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000"),
    )
    rtcp_src = make("udpsrc", "rtcp_src")
    rtcp_src.set_property("port", a.rtcp_port)
    rtcp_src.set_property("caps", Gst.Caps.from_string("application/x-rtcp"))
    rtcp_sink = make("udpsink", "rtcp_sink")
    rtcp_sink.set_property("host", a.host)
    rtcp_sink.set_property("port", a.rtcp_feedback_port)
    rtcp_sink.set_property("sync", False)
    rtcp_sink.set_property("async", False)
    depay = make("rtph264depay", "depay")
    parse = make("h264parse", "parse")
    dec = make("avdec_h264", "dec")
    sink = make("fakesink", "sink")
    sink.set_property("sync", False)
    sink.set_property("async", False)
    rtxrecv = make("rtprtxreceive", "rtxrecv")
    rtxrecv.set_property("payload-type-map", pt_map_structure())

    # rtxrecv 由 rtpbin 在 aux 信号回调中自行 add 并接线，不能提前加入管线
    for el in (rtp_src, rtcp_src, rtcp_sink, rtpbin, depay, parse, dec, sink):
        p.add(el)

    holder = {"rtxrecv": rtxrecv, "jb": None}

    def aux_receiver(bin_, session):
        if session != 0:
            return None
        # Canonical form (client-rtpaux.c): a bin with ghost pads, not the raw element.
        b = Gst.Bin.new("rtxrecv-bin")
        b.add(rtxrecv)
        b.add_pad(Gst.GhostPad.new("src_0", rtxrecv.get_static_pad("src")))
        b.add_pad(Gst.GhostPad.new("sink_0", rtxrecv.get_static_pad("sink")))
        return b

    def request_jb(bin_, session):
        # rtpbin owns the jitterbuffer: create it here, do NOT add it to the pipeline.
        # Leave rtx-* at their automatic defaults (the C example sets nothing).
        jb = make("rtpjitterbuffer", "jb")
        jb.set_property("latency", a.latency)
        jb.set_property("do-lost", True)
        jb.set_property("do-retransmission", not a.no_rtx)
        holder["jb"] = jb
        return jb

    def pt_map(bin_, session, pt):
        # Required: rtpbin must be able to resolve the RTX payload type, and the
        # media caps must advertise NACK/PLI support for feedback to be scheduled.
        if session != 0:
            return None
        if pt == 96:
            return Gst.Caps.from_string(
                "application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000,"
                "rtcp-fb-nack=(boolean)true,rtcp-fb-nack-pli=(boolean)true")
        if pt == 97:
            return Gst.Caps.from_string(
                "application/x-rtp,media=video,encoding-name=rtx,payload=97,clock-rate=90000")
        return None

    rtpbin.connect("request-aux-receiver", aux_receiver)
    rtpbin.connect("request-jitterbuffer", request_jb)
    rtpbin.connect("request-pt-map", pt_map)

    def pad_added(bin_, pad):
        name = pad.get_name()
        if name.startswith("recv_rtp_src_"):
            pad.link(depay.get_static_pad("sink"))
        elif name.startswith("send_rtcp_src_"):
            pad.link(rtcp_sink.get_static_pad("sink"))
            probe_rtcp(pad, stats, "out")
    rtpbin.connect("pad-added", pad_added)

    rtp_src.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtp_sink_0"))
    rtcp_src.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtcp_sink_0"))
    rtcp_out = rtpbin.request_pad_simple("send_rtcp_src_0")
    if rtcp_out is not None:
        ok = rtcp_out.link(rtcp_sink.get_static_pad("sink"))
        stats["rtcp_link_ok"] = int(bool(ok))
        stats["rtcp_is_linked"] = int(rtcp_out.is_linked())
        probe_rtcp(rtcp_out, stats, "out")
        probe_count(rtcp_sink.get_static_pad("sink"), stats, "rtcp_into_udpsink")
    else:
        stats["rtcp_link_ok"] = -1
    depay.link(parse)
    parse.link(dec)
    dec.link(sink)
    probe_count(dec.get_static_pad("src"), stats, "decoded_frames")
    return p, holder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["sender", "receiver"])
    ap.add_argument("--file", default="/home/bai/rtc_test/clip10.mp4")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--rtp-port", type=int, default=5004)
    ap.add_argument("--rtcp-port", type=int, default=5006)
    ap.add_argument("--rtcp-feedback-port", type=int, default=5005)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--latency", type=int, default=500)
    ap.add_argument("--no-rtx", action="store_true")
    ap.add_argument("--seconds", type=float, default=30.0)
    a = ap.parse_args()

    stats = {}
    holder = {}
    if a.role == "sender":
        p, rtxsend = build_sender(a, stats)
    else:
        p, holder = build_receiver(a, stats)
        rtxsend = None

    loop = GLib.MainLoop()

    def on_msg(bus, msg):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print("ERROR %s %s" % (err.message, dbg), flush=True)
            loop.quit()
        elif msg.type == Gst.MessageType.EOS:
            loop.quit()
        elif msg.type == Gst.MessageType.WARNING:
            err, _ = msg.parse_warning()
            print("WARN %s" % err.message, flush=True)

    bus = p.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_msg)

    if p.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        print("FAILED", flush=True)
        return 2

    def stop():
        try:
            p.send_event(Gst.Event.new_eos())
        except Exception:
            pass
        return False
    GLib.timeout_add(int(a.seconds * 1000), stop)
    GLib.timeout_add(int((a.seconds + 5) * 1000), lambda: (loop.quit(), False)[1])

    loop.run()
    p.set_state(Gst.State.NULL)

    result = {"role": a.role, "loss": a.loss, "no_rtx": a.no_rtx, "stats": stats}
    if a.role == "sender" and rtxsend is not None:
        result["rtxsend"] = {
            "requests": rtxsend.get_property("num-rtx-requests"),
            "packets": rtxsend.get_property("num-rtx-packets"),
        }
    if a.role == "receiver":
        rx = holder.get("rtxrecv")
        if rx is not None:
            result["rtxrecv"] = {
                "requests": rx.get_property("num-rtx-requests"),
                "packets": rx.get_property("num-rtx-packets"),
                "assoc": rx.get_property("num-rtx-assoc-packets"),
            }
        jb = holder.get("jb")
        if jb is not None:
            st = jb.get_property("stats")
            d = {}
            for i in range(st.n_fields()):
                name = st.nth_field_name(i)
                d[name] = st.get_value(name)
            result["jitterbuffer"] = d
    print("RESULT " + json.dumps(result, default=str), flush=True)
    # PyGI teardown of rtpbin+RTX occasionally segfaults; stats are already out.
    import os
    os._exit(0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
