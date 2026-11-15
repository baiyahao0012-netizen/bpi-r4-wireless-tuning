#!/usr/bin/env python3
"""T7 lab: NACK / RTX / PLI over rtpsession (the official GStreamer combination).

sender   file -> h264parse -> rtph264pay(96) -> rtprtxsend -> rtpsession(avpf)
         rtpsession.send_rtp_src -> [identity drop-probability] -> udpsink 5004
         rtpsession.send_rtcp_src -> udpsink 5006
         udpsrc 5005 -> rtpsession.recv_rtcp_sink

receiver udpsrc 5004 -> rtpsession(avpf)
         rtpsession.recv_rtp_src -> rtprtxreceive -> rtpssrcdemux -> rtpjitterbuffer
（rtpssrcdemux 给 RTR 上游事件补 ssrc；缺它会话 find_source 失败，NACK 不调度）
         jitterbuffer(do-retransmission) -> rtph264depay -> h264parse -> avdec_h264
         rtpsession.send_rtcp_src -> udpsink 5005
         udpsrc 5006 -> rtpsession.recv_rtcp_sink
"""
import argparse
import json
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib, GObject  # noqa: E402

Gst.init(None)

PT_NAMES = {200: "SR", 201: "RR", 205: "NACK", 206: "PLI"}
HOLDER = {}


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
    raise RuntimeError("bad pt map")


def probe_buffer(info):
    for name in ("get_buffer", "get_current_buffer"):
        fn = getattr(info, name, None)
        if fn is not None:
            try:
                b = fn()
                if b is not None:
                    return b
            except Exception:
                pass
    try:
        if isinstance(info.data, Gst.Buffer):
            return info.data
    except Exception:
        pass
    return None


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
        ln = ((data[i + 2] << 8) | data[i + 3]) * 4 + 4
        out.append(pt)
        if ln <= 0:
            break
        i += ln
    return out


def rtp_pt(buf):
    try:
        data = bytes(buf.extract_dup(0, buf.get_size()))
    except Exception:
        return None
    if len(data) >= 2 and (data[0] >> 6) == 2:
        return data[1] & 0x7f
    return None


def probe_rtp_pt(pad, stats, tag):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            pt = rtp_pt(buf)
            if pt is not None:
                k = "%s_pt%d" % (tag, pt)
                stats[k] = stats.get(k, 0) + 1
                try:
                    data = bytes(buf.extract_dup(0, buf.get_size()))
                    if len(data) >= 12 and "ssrc" not in stats:
                        stats["ssrc"] = int.from_bytes(data[8:12], "big")
                except Exception:
                    pass
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_rtcp(pad, stats, tag):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            for pt in rtcp_pts(buf):
                k = "%s_%s" % (tag, PT_NAMES.get(pt, str(pt)))
                stats[k] = stats.get(k, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_count(pad, stats, key):
    def cb(p, info):
        stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def build_sender(a, stats):
    p = Gst.Pipeline.new("sender")
    src = make("filesrc", "src")
    src.set_property("location", a.file)
    demux = make("qtdemux", "demux")
    parse = make("h264parse", "parse")
    pay = make("rtph264pay", "pay")
    pay.set_property("pt", 96)
    pay.set_property("config-interval", 1)
    rtx = make("rtprtxsend", "rtxsend")
    rtx.set_property("payload-type-map", pt_map_structure())
    rtx.set_property("max-size-packets", 5000)
    rtx.set_property("max-size-time", 5000)
    sess = make("rtpsession", "sess")
    sess.set_property("rtp-profile", 3)  # AVPF（枚举：1=avp, 3=avpf）
    drop = make("identity", "drop")
    drop.set_property("drop-probability", a.loss)
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
    rtcp_src.set_property("port", a.feedback_port)
    rtcp_src.set_property("caps", Gst.Caps.from_string("application/x-rtcp"))

    for el in (src, demux, parse, pay, rtx, sess, drop, rtp_sink, rtcp_sink, rtcp_src):
        p.add(el)

    src.link(demux)

    def demux_pad(b, pad):
        if pad.get_name().startswith("video"):
            pad.link(parse.get_static_pad("sink"))
    demux.connect("pad-added", demux_pad)
    parse.link(pay)
    pay.link(rtx)

    # Link the RTCP feedback leg FIRST: the session's receive pads must be
    # active before the RTP side starts pushing, otherwise udpsrc is stopped.
    fb = sess.request_pad_simple("recv_rtcp_sink")
    rtcp_q = make("queue", "rtcp_q")
    p.add(rtcp_q)
    rtcp_q.get_static_pad("src").link(fb)
    link_ret = rtcp_src.get_static_pad("src").link(rtcp_q.get_static_pad("sink"))
    stats["rtcp_src_link_ret"] = getattr(link_ret, "value_nick", str(link_ret))
    probe_count(rtcp_src.get_static_pad("src"), stats, "rtcp_in_raw")
    probe_rtcp(fb, stats, "in")

    rtx.get_static_pad("src").link(sess.request_pad_simple("send_rtp_sink"))
    sess.get_static_pad("send_rtp_src").link(drop.get_static_pad("sink"))
    rtcp_pad = sess.request_pad_simple("send_rtcp_src")
    rtcp_pad.link(rtcp_sink.get_static_pad("sink"))
    probe_rtcp(rtcp_pad, stats, "out")

    drop.link(rtp_sink)
    probe_count(drop.get_static_pad("src"), stats, "rtp_sent")
    probe_rtp_pt(drop.get_static_pad("src"), stats, "out")
    stats["rtcp_src_port"] = rtcp_src.get_property("port")
    stats["rtcp_src_src_linked"] = int(rtcp_src.get_static_pad("src").is_linked())
    stats["fb_linked"] = int(fb.is_linked())
    HOLDER["fb"] = fb
    HOLDER["rtcp_src"] = rtcp_src

    # 可选：补一条 dummy RTP 接收腿，测试只发会话是否因此激活 NACK 处理
    if a.dummy_recv:
        dummy = make("udpsrc", "dummy")
        dummy.set_property("port", 5010)
        dummy.set_property("caps", Gst.Caps.from_string("application/x-rtp"))
        p.add(dummy)
        dummy.get_static_pad("src").link(sess.request_pad_simple("recv_rtp_sink"))
    return p, rtx, sess


def build_receiver(a, stats):
    p = Gst.Pipeline.new("receiver")
    rtp_src = make("udpsrc", "rtp_src")
    rtp_src.set_property("port", a.rtp_port)
    # T3/T4 already showed this path needs a big socket buffer; without it the
    # kernel drops bursts and every arm looks lossy (A arm: 265/302 instead of 302).
    rtp_src.set_property("buffer-size", 8 * 1024 * 1024)
    rtp_src.set_property(
        "caps",
        Gst.Caps.from_string(
            "application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000"),
    )
    sess = make("rtpsession", "sess")
    sess.set_property("rtp-profile", 3)  # AVPF（枚举：1=avp, 3=avpf）
    if a.bandwidth > 0:
        # bytes/s; RTCP gets 5% of it. Larger -> shorter computed T_rr, which is
        # what gates early feedback (rtcp-min-interval alone is only a floor).
        sess.set_property("bandwidth", a.bandwidth)
    if a.rtcp_min_interval:
        sess.set_property("rtcp-min-interval", a.rtcp_min_interval)

    def ptmap_cb(_sess, _pt):
        return Gst.Caps.from_string(
            "application/x-rtp,media=video,encoding-name=H264,clock-rate=90000,"
            "rtcp-fb-nack=(boolean)true,rtcp-fb-nack-pli=(boolean)true")
    sess.connect("request-pt-map", ptmap_cb)

    rtx = make("rtprtxreceive", "rtxrecv")
    rtx.set_property("payload-type-map", pt_map_structure())
    demux = make("rtpssrcdemux", "demux")
    jb = make("rtpjitterbuffer", "jb")
    jb.set_property("latency", a.latency)
    jb.set_property("do-lost", True)
    jb.set_property("do-retransmission", not a.no_rtx)
    # Keep rtx-delay / rtx-retry-timeout / rtx-max-retries at their defaults
    # (-1 = automatic). GStreamer derives them from the measured RTT
    # (DEFAULT_AUTO_RTX_DELAY 20ms, DEFAULT_AUTO_RTX_TIMEOUT 40ms); hard-coding
    # 0 disables that logic and starves the retransmission scheduling.
    if a.rtx_manual and not a.no_rtx:
        jb.set_property("rtx-max-retries", 8)
        jb.set_property("rtx-delay", 0)
        jb.set_property("rtx-min-delay", 0)
    if a.rtx_retry_period > 0:
        # How long the jitterbuffer keeps asking for a missing packet. This is
        # the max_delay handed to rtpsession: if it is shorter than the RTCP
        # interval, the NACK expires before a packet can be sent.
        jb.set_property("rtx-retry-period", a.rtx_retry_period)
    if a.rtx_retry_timeout > 0:
        jb.set_property("rtx-retry-timeout", a.rtx_retry_timeout)
    if a.rtx_max_retries >= 0:
        # Cap how many times the same packet may be re-requested; this bounds
        # the NACK volume that can turn into an RTCP storm.
        jb.set_property("rtx-max-retries", a.rtx_max_retries)
    try:
        jb.set_property("send-keyframe-request", True)
    except Exception:
        pass
    depay = make("rtph264depay", "depay")
    parse = make("h264parse", "parse")
    dec = make("avdec_h264", "dec")
    sink = make("fakesink", "sink")
    sink.set_property("sync", False)
    sink.set_property("async", False)
    rtcp_sink = make("udpsink", "rtcp_sink")
    rtcp_sink.set_property("host", a.host)
    rtcp_sink.set_property("port", a.feedback_port)
    rtcp_sink.set_property("sync", False)
    rtcp_sink.set_property("async", False)
    rtcp_src = make("udpsrc", "rtcp_src")
    rtcp_src.set_property("port", a.rtcp_port)
    rtcp_src.set_property("caps", Gst.Caps.from_string("application/x-rtcp"))

    for el in (rtp_src, sess, rtx, demux, jb, depay, parse, dec, sink, rtcp_sink, rtcp_src):
        p.add(el)

    probe_rtp_pt(rtp_src.get_static_pad("src"), stats, "net")
    rtp_src.get_static_pad("src").link(sess.request_pad_simple("recv_rtp_sink"))
    rtcp_pad = sess.request_pad_simple("send_rtcp_src")
    rtcp_pad.link(rtcp_sink.get_static_pad("sink"))
    probe_rtcp(rtcp_pad, stats, "out")
    probe_rtp_pt(sess.get_static_pad("recv_rtp_src"), stats, "in")

    # 隔离开关：跳过 rtprtxreceive，直接会话 -> demux -> jitterbuffer
    if a.no_rtxrecv:
        sess.get_static_pad("recv_rtp_src").link(demux.get_static_pad("sink"))
    else:
        sess.get_static_pad("recv_rtp_src").link(rtx.get_static_pad("sink"))
        rtx.link(demux)

    # demux 的 src pad 是按 SSRC 请求生成的，new-ssrc-pad 后再接到 jb
    def demux_pad(d, ssrc, pad):
        pad.link(jb.get_static_pad("sink"))
    demux.connect("new-ssrc-pad", demux_pad)
    jb.link(depay)
    depay.link(parse)
    parse.link(dec)
    dec.link(sink)
    probe_count(dec.get_static_pad("src"), stats, "decoded_frames")
    fb = sess.request_pad_simple("recv_rtcp_sink")
    rtcp_src.get_static_pad("src").link(fb)
    probe_count(rtcp_src.get_static_pad("src"), stats, "rtcp_in_raw")
    HOLDER["sess"] = sess
    HOLDER["jb"] = jb
    HOLDER["rtx"] = rtx
    HOLDER["demux"] = demux
    HOLDER["depay"] = depay
    HOLDER["parse"] = parse
    HOLDER["dec"] = dec
    return p, rtx, jb, sess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["sender", "receiver"])
    ap.add_argument("--file", default="/home/bai/rtc_test/clip10.mp4")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--rtp-port", type=int, default=5004)
    ap.add_argument("--rtcp-port", type=int, default=5006)
    ap.add_argument("--feedback-port", type=int, default=5005)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--latency", type=int, default=500)
    ap.add_argument("--no-rtx", action="store_true")
    ap.add_argument("--dummy-recv", action="store_true")
    ap.add_argument("--no-rtxrecv", action="store_true")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--rtcp-min-interval", type=int, default=0,
                    help="min regular RTCP interval in ns; 0 keeps the default")
    ap.add_argument("--rtx-manual", action="store_true",
                    help="reproduce the old hard-coded rtx-delay=0 / max-retries=8")
    ap.add_argument("--rtx-retry-period", type=int, default=0,
                    help="jitterbuffer rtx-retry-period in ms (0 keeps default)")
    ap.add_argument("--rtx-retry-timeout", type=int, default=0,
                    help="jitterbuffer rtx-retry-timeout in ms (0 keeps default)")
    ap.add_argument("--rtx-max-retries", type=int, default=-1,
                    help="max retransmission requests per packet (-1 unlimited)")
    ap.add_argument("--bandwidth", type=float, default=0,
                    help="session bandwidth in bytes/s (0 keeps the default)")
    a = ap.parse_args()

    stats = {}
    if a.role == "sender":
        p, rtx, sess = build_sender(a, stats)
    else:
        p, rtx, jb, sess = build_receiver(a, stats)

    def session_stats():
        out = {}
        try:
            st = sess.get_property("stats")
            for i in range(st.n_fields()):
                nm = st.nth_field_name(i)
                if "nack" in nm or "rtx" in nm:
                    out[nm] = st.get_value(nm)
        except Exception as exc:
            out["err"] = str(exc)
        return out

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

    def sample():
        fb = HOLDER.get("fb")
        src = HOLDER.get("rtcp_src")
        if fb is not None:
            stats["fb_active_at2s"] = int(fb.is_active())
        if src is not None:
            try:
                stats["srcpad_active_at2s"] = int(src.get_static_pad("src").is_active())
                stats["src_state_at2s"] = src.get_state(0)[1].value_nick
            except Exception as exc:
                stats["sample_err"] = str(exc)
        return False

    def force_key_unit():
        sess = HOLDER.get("sess")
        jb = HOLDER.get("jb")
        rtx = HOLDER.get("rtx")
        demux = HOLDER.get("demux")
        depay = HOLDER.get("depay")
        parse = HOLDER.get("parse")
        dec = HOLDER.get("dec")
        ssrc = stats.get("ssrc")
        if sess is not None and jb is not None and ssrc is not None:
            try:
                st = Gst.Structure.new_empty("GstForceKeyUnit")
                v = GObject.Value()
                v.init(GObject.TYPE_UINT)
                v.set_uint(ssrc)
                st.set_value("ssrc", v)
                v2 = GObject.Value()
                v2.init(GObject.TYPE_UINT)
                v2.set_uint(96)
                st.set_value("payload", v2)
                v3 = GObject.Value()
                v3.init(GObject.TYPE_BOOLEAN)
                v3.set_boolean(False)
                st.set_value("all-headers", v3)
                targets = []
                for el in (dec, parse, depay, jb, demux, rtx):
                    if el is not None:
                        pad = el.get_static_pad("sink")
                        if pad is not None:
                            targets.append(pad)
                ok = False
                for pad in targets:
                    ev = Gst.Event.new_custom(
                        Gst.EventType.CUSTOM_UPSTREAM, st.copy())
                    if pad.push_event(ev):
                        ok = True
                        break
                stats["force_key_unit_sent"] = int(ok)
            except Exception as exc:
                stats["force_key_unit_err"] = str(exc)
        return False

    def sample_counters():
        """Snapshot the RTX counters while the pipeline is still running."""
        try:
            d = {
                "requests": rtx.get_property("num-rtx-requests"),
                "packets": rtx.get_property("num-rtx-packets"),
            }
            if a.role != "sender":
                d["assoc"] = rtx.get_property("num-rtx-assoc-packets")
            stats["rtx_last"] = d
        except Exception as exc:
            stats["rtx_last_err"] = str(exc)
        s = session_stats()
        if "err" not in s:
            stats["session_last"] = s
        return True

    GLib.timeout_add(1000, sample_counters)
    GLib.timeout_add(2000, sample)
    if a.role == "receiver":
        GLib.timeout_add(3000, force_key_unit)
    GLib.timeout_add(int(a.seconds * 1000), stop)
    GLib.timeout_add(int((a.seconds + 5) * 1000), lambda: (loop.quit(), False)[1])

    loop.run()
    p.set_state(Gst.State.NULL)

    result = {"role": a.role, "loss": a.loss, "no_rtx": a.no_rtx, "stats": stats}
    # rtprtxsend/rtprtxreceive zero their counters on PAUSED->READY
    # (gstrtprtxsend.c:1292, gstrtprtxreceive.c:1073), so the post-NULL read is
    # kept only to document that behaviour; rtx_mid is the evidence.
    result["rtx_mid"] = stats.get("rtx_last")
    result["session_mid"] = stats.get("session_last")
    if a.role == "sender":
        result["rtx_after_null"] = {
            "requests": rtx.get_property("num-rtx-requests"),
            "packets": rtx.get_property("num-rtx-packets"),
        }
    else:
        result["rtx_after_null"] = {
            "requests": rtx.get_property("num-rtx-requests"),
            "packets": rtx.get_property("num-rtx-packets"),
            "assoc": rtx.get_property("num-rtx-assoc-packets"),
        }
        st = jb.get_property("stats")
        d = {}
        for i in range(st.n_fields()):
            nm = st.nth_field_name(i)
            d[nm] = st.get_value(nm)
        result["jitterbuffer"] = d

    result["session_after_null"] = session_stats()
    print("RESULT " + json.dumps(result, default=str), flush=True)
    import os
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
