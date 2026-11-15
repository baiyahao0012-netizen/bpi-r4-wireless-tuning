#!/usr/bin/env python3
"""T8 lab: two RTP sessions (video H264 PT96 + audio Opus PT111) over rtpbin.

Mirrors the canonical GStreamer example tests/examples/rtp/client-rtpaux.c:
two sessions on one rtpbin, per-session jitterbuffer, RTCP SR on each.

sender   anchor.mkv -> matroskademux
           video -> h264parse -> rtph264pay(96) -> rtpbin.send_rtp_sink_0
           audio -> opusparse -> rtpopuspay(111) -> rtpbin.send_rtp_sink_1
         rtpbin.send_rtp_src_0 -> udpsink 5004 ; _1 -> udpsink 5008
         rtpbin.send_rtcp_src_0 -> udpsink 5006 ; _1 -> udpsink 5010
         udpsrc 5005 -> recv_rtcp_sink_0 ; udpsrc 5009 -> recv_rtcp_sink_1

receiver udpsrc 5004 -> recv_rtp_sink_0 ; udpsrc 5008 -> recv_rtp_sink_1
         recv_rtp_src_0 -> depay -> parse -> dec -> I420 -> filesink
         recv_rtp_src_1 -> opusdepay -> opusdec -> S16LE mono 48k -> filesink
         RTCP mirrored on 5005/5006 and 5009/5010

Prints a RESULT json with RTCP SR records (per session) and buffer counts.
"""
import argparse
import json
import struct
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib, GObject  # noqa: E402

Gst.init(None)

HOLDER = {}


def pt_map_struct(pt, rtx_pt):
    res = Gst.Structure.from_string("application/x-rtp-pt-map,%d=(uint)%d" % (pt, rtx_pt))
    for item in res:
        if isinstance(item, Gst.Structure):
            return item
    raise RuntimeError("bad pt map")


def make(factory, name):
    el = Gst.ElementFactory.make(factory, name)
    if el is None:
        raise RuntimeError("missing element: %s" % factory)
    return el


def caps(s):
    return Gst.Caps.from_string(s)


def parse_rtcp_sr(buf):
    """Return (pt, ssrc, ntp, rtp_ts) for each SR found in a compound packet."""
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
        if pt == 200 and i + 28 <= len(data):
            ssrc = struct.unpack("!I", data[i + 4:i + 8])[0]
            ntp = struct.unpack("!Q", data[i + 8:i + 16])[0]
            rtp_ts = struct.unpack("!I", data[i + 16:i + 20])[0]
            out.append((pt, ssrc, ntp, rtp_ts))
        if ln <= 0:
            break
        i += ln
    return out


def probe_sr(pad, stats, key):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            for pt, ssrc, ntp, rtp_ts in parse_rtcp_sr(buf):
                stats.setdefault(key, []).append(
                    {"ssrc": ssrc, "ntp": ntp, "rtp_ts": rtp_ts})
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


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


def probe_count(pad, stats, key):
    def cb(p, info):
        stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


RTCP_PT_NAMES = {200: "SR", 201: "RR", 205: "NACK", 206: "PLI"}


def probe_rtcp_pt(pad, stats, prefix):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is None:
            return Gst.PadProbeReturn.OK
        try:
            data = bytes(buf.extract_dup(0, buf.get_size()))
        except Exception:
            return Gst.PadProbeReturn.OK
        i = 0
        while i + 4 <= len(data):
            if (data[i] >> 6) != 2:
                break
            pt = data[i + 1]
            ln = ((data[i + 2] << 8) | data[i + 3]) * 4 + 4
            key = "%s_%s" % (prefix, RTCP_PT_NAMES.get(pt, str(pt)))
            stats[key] = stats.get(key, 0) + 1
            if ln <= 0:
                break
            i += ln
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_keyframe_event(pad, stats):
    def cb(p, info):
        ev = None
        for name in ("get_event",):
            fn = getattr(info, name, None)
            if fn is not None:
                try:
                    ev = fn()
                except Exception:
                    ev = None
        if ev is None:
            ev = getattr(info, "event", None)
        if ev is not None:
            try:
                st = ev.get_structure()
            except Exception:
                st = None
            if st is not None and st.get_name() == "GstForceKeyUnit":
                stats["keyframe_events"] = stats.get("keyframe_events", 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, cb)


def probe_rtp_ssrc(pad, stats):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None and "video_ssrc" not in stats:
            try:
                data = bytes(buf.extract_dup(0, 12))
                if len(data) >= 12 and (data[0] >> 6) == 2:
                    stats["video_ssrc"] = struct.unpack("!I", data[8:12])[0]
            except Exception:
                pass
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_rtp_pt(pad, stats, prefix):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            try:
                data = bytes(buf.extract_dup(0, min(buf.get_size(), 16)))
            except Exception:
                return Gst.PadProbeReturn.OK
            if len(data) >= 2 and (data[0] >> 6) == 2:
                pt = data[1] & 0x7F
                key = "%s_pt%d" % (prefix, pt)
                stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


VIDEO_CAPS = ("application/x-rtp,media=video,encoding-name=H264,payload=96,"
              "clock-rate=90000,rtcp-fb-nack=(boolean)true,rtcp-fb-nack-pli=(boolean)true")
AUDIO_CAPS = ("application/x-rtp,media=audio,encoding-name=OPUS,payload=111,"
              "clock-rate=48000,rtcp-fb-nack=(boolean)true")


def build_sender(a, stats):
    p = Gst.Pipeline.new("t8-sender")
    rtpbin = make("rtpbin", "rtpbin")
    rtpbin.set_property("latency", a.latency)
    rtpbin.set_property("do-retransmission", False)
    rtpbin.set_property("rtp-profile", 3)  # AVPF
    vparse = make("h264parse", "vparse")
    vpay = make("rtph264pay", "vpay")
    vpay.set_property("pt", 96)
    vpay.set_property("config-interval", 1)
    aparse = make("opusparse", "aparse")
    apay = make("rtpopuspay", "apay")
    apay.set_property("pt", 111)
    src_elems = []
    if a.synthetic:
        vsrc = make("videotestsrc", "vsrc")
        vsrc.set_property("is-live", True)
        vcap = make("capsfilter", "vcaps")
        vcap.set_property("caps", caps("video/x-raw,width=%d,height=%d,framerate=30/1"
                                       % (a.width, a.height)))
        venc = make("openh264enc", "venc")
        venc.set_property("bitrate", 2000000)
        asrc = make("audiotestsrc", "asrc")
        asrc.set_property("is-live", True)
        asrc.set_property("wave", "sine")
        asrc.set_property("freq", 1000)
        aenc = make("opusenc", "aenc")
        src_elems = [vsrc, vcap, venc, asrc, aenc]
    else:
        src = make("filesrc", "src")
        src.set_property("location", a.file)
        demux = make("matroskademux", "demux")
        src_elems = [src, demux]
    v_sink = make("udpsink", "v_sink")
    v_sink.set_property("host", a.host)
    v_sink.set_property("port", a.video_rtp_port)
    v_sink.set_property("sync", False)
    v_sink.set_property("async", False)
    v_drop = make("identity", "v_drop")
    v_drop.set_property("drop-probability", a.video_loss)
    a_sink = make("udpsink", "a_sink")
    a_sink.set_property("host", a.host)
    a_sink.set_property("port", a.audio_rtp_port)
    a_sink.set_property("sync", False)
    a_sink.set_property("async", False)
    a_drop = make("identity", "a_drop")
    a_drop.set_property("drop-probability", a.audio_loss)
    v_rtcp_sink = make("udpsink", "v_rtcp_sink")
    v_rtcp_sink.set_property("host", a.host)
    v_rtcp_sink.set_property("port", a.video_rtcp_port)
    v_rtcp_sink.set_property("sync", False)
    v_rtcp_sink.set_property("async", False)
    a_rtcp_sink = make("udpsink", "a_rtcp_sink")
    a_rtcp_sink.set_property("host", a.host)
    a_rtcp_sink.set_property("port", a.audio_rtcp_port)
    a_rtcp_sink.set_property("sync", False)
    a_rtcp_sink.set_property("async", False)
    if a.bind_address:
        # Force the media source address so the source-based policy route keeps
        # the traffic on the wireless interface instead of the management one.
        for s in (v_sink, a_sink, v_rtcp_sink, a_rtcp_sink):
            s.set_property("bind-address", a.bind_address)
    v_fb = make("udpsrc", "v_fb")
    v_fb.set_property("port", a.video_feedback_port)
    v_fb.set_property("caps", caps("application/x-rtcp"))
    a_fb = make("udpsrc", "a_fb")
    a_fb.set_property("port", a.audio_feedback_port)
    a_fb.set_property("caps", caps("application/x-rtcp"))

    for el in (vparse, vpay, aparse, apay, rtpbin,
               v_sink, v_drop, a_sink, a_drop, v_rtcp_sink, a_rtcp_sink, v_fb, a_fb):
        p.add(el)
    for el in src_elems:
        p.add(el)
    a_drop.link(a_sink)
    v_drop.link(v_sink)
    probe_keyframe_event(vpay.get_static_pad("sink"), stats)
    probe_keyframe_event(venc.get_static_pad("src"), stats) if a.synthetic else None

    if a.synthetic:
        vsrc.link(vcap)
        vcap.link(venc)
        venc.link(vparse)
        asrc.link(aenc)
        aenc.link(apay)
    else:
        src.link(demux)

        def demux_pad(b, pad):
            name = pad.get_name()
            if name.startswith("video"):
                pad.link(vparse.get_static_pad("sink"))
            elif name.startswith("audio"):
                pad.link(aparse.get_static_pad("sink"))
        demux.connect("pad-added", demux_pad)
        aparse.link(apay)
    vparse.link(vpay)

    def pt_map(b, session, pt):
        if session == 0 and pt == 96:
            return caps(VIDEO_CAPS)
        if session == 1 and pt == 111:
            return caps(AUDIO_CAPS)
        if session == 1 and pt == 112:
            return caps("application/x-rtp,media=audio,encoding-name=rtx,"
                        "payload=112,clock-rate=48000")
        return None
    rtpbin.connect("request-pt-map", pt_map)

    def aux_sender(b, session):
        if session != 1:
            return None
        box = Gst.Bin.new("audio-rtxsend")
        rtx = make("rtprtxsend", "artxsend")
        rtx.set_property("payload-type-map", pt_map_struct(111, 112))
        box.add(rtx)
        box.add_pad(Gst.GhostPad.new("sink_1", rtx.get_static_pad("sink")))
        box.add_pad(Gst.GhostPad.new("src_1", rtx.get_static_pad("src")))
        return box
    rtpbin.connect("request-aux-sender", aux_sender)

    def pad_added(b, pad):
        n = pad.get_name()
        stats.setdefault("pad_added", []).append(n)
        if n.startswith("send_rtp_src_0"):
            pad.link(v_drop.get_static_pad("sink"))
        elif n.startswith("send_rtp_src_1"):
            pad.link(a_drop.get_static_pad("sink"))
        elif n.startswith("send_rtcp_src_0"):
            pass  # linked explicitly below
        elif n.startswith("send_rtcp_src_1"):
            pass
    rtpbin.connect("pad-added", pad_added)

    vpay.get_static_pad("src").link(rtpbin.request_pad_simple("send_rtp_sink_0"))
    apay.get_static_pad("src").link(rtpbin.request_pad_simple("send_rtp_sink_1"))
    v_fb.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtcp_sink_0"))
    a_fb.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtcp_sink_1"))
    probe_rtcp_pt(rtpbin.request_pad_simple("recv_rtcp_sink_0"), stats, "rtcp_in")
    for sess, sink, key in ((0, v_rtcp_sink, "sr_video"), (1, a_rtcp_sink, "sr_audio")):
        pad = rtpbin.request_pad_simple("send_rtcp_src_%u" % sess)
        if pad is not None:
            pad.link(sink.get_static_pad("sink"))
            probe_sr(pad, stats, key)
    return p


def build_receiver(a, stats):
    p = Gst.Pipeline.new("t8-receiver")
    rtpbin = make("rtpbin", "rtpbin")
    rtpbin.set_property("latency", a.latency)
    rtpbin.set_property("do-retransmission", not a.no_audio_rtx)
    if a.force_keyframe:
        # Let the jitterbuffers report losses downstream; rtph264depay turns
        # those into GstForceKeyUnit, which the session converts to PLI.
        rtpbin.set_property("do-lost", True)
    rtpbin.set_property("rtp-profile", 3)
    v_src = make("udpsrc", "v_src")
    v_src.set_property("port", a.video_rtp_port)
    v_src.set_property("buffer-size", 8 * 1024 * 1024)
    v_src.set_property("caps", caps("application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000"))
    a_src = make("udpsrc", "a_src")
    a_src.set_property("port", a.audio_rtp_port)
    a_src.set_property("buffer-size", 8 * 1024 * 1024)
    a_src.set_property("caps", caps("application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000"))
    v_rtcp_src = make("udpsrc", "v_rtcp_src")
    v_rtcp_src.set_property("port", a.video_rtcp_port)
    v_rtcp_src.set_property("caps", caps("application/x-rtcp"))
    a_rtcp_src = make("udpsrc", "a_rtcp_src")
    a_rtcp_src.set_property("port", a.audio_rtcp_port)
    a_rtcp_src.set_property("caps", caps("application/x-rtcp"))
    v_rtcp_sink = make("udpsink", "v_rtcp_sink")
    v_rtcp_sink.set_property("host", a.host)
    v_rtcp_sink.set_property("port", a.video_feedback_port)
    v_rtcp_sink.set_property("sync", False)
    v_rtcp_sink.set_property("async", False)
    a_rtcp_sink = make("udpsink", "a_rtcp_sink")
    a_rtcp_sink.set_property("host", a.host)
    a_rtcp_sink.set_property("port", a.audio_feedback_port)
    a_rtcp_sink.set_property("sync", False)
    a_rtcp_sink.set_property("async", False)
    vdepay = make("rtph264depay", "vdepay")
    if a.force_keyframe:
        try:
            vdepay.set_property("request-keyframe", True)
            # gstrtph264depay.c:237 seeds waiting_for_keyframe from this one;
            # without it the request-keyframe branch (line 1126) never runs.
            vdepay.set_property("wait-for-keyframe", True)
        except Exception:
            pass
    vparse = make("h264parse", "vparse")
    vdec = make("avdec_h264", "vdec")
    vconv = make("videoconvert", "vconv")
    vscale = make("videoscale", "vscale")
    vcap = make("capsfilter", "vcap")
    vcap.set_property("caps", caps("video/x-raw,format=I420,width=320,height=180"))
    vsink = make("filesink", "vsink")
    vsink.set_property("location", a.video_out)
    adepay = make("rtpopusdepay", "adepay")
    adec = make("opusdec", "adec")
    aconv = make("audioconvert", "aconv")
    ares = make("audioresample", "ares")
    acap = make("capsfilter", "acap")
    acap.set_property("caps", caps("audio/x-raw,format=S16LE,channels=1,rate=48000"))
    asink = make("filesink", "asink")
    asink.set_property("location", a.audio_out)

    for el in (v_src, a_src, v_rtcp_src, a_rtcp_src, v_rtcp_sink, a_rtcp_sink,
               rtpbin, vdepay, vparse, vdec, vconv, vscale, vcap, vsink,
               adepay, adec, aconv, ares, acap, asink):
        p.add(el)

    def pt_map(b, session, pt):
        if session == 0 and pt == 96:
            return caps(VIDEO_CAPS)
        if session == 1 and pt == 111:
            return caps(AUDIO_CAPS)
        if session == 1 and pt == 112:
            return caps("application/x-rtp,media=audio,encoding-name=rtx,"
                        "payload=112,clock-rate=48000")
        return None
    rtpbin.connect("request-pt-map", pt_map)

    def aux_receiver(b, session):
        if session != 1 or a.no_audio_rtx:
            return None
        box = Gst.Bin.new("audio-rtxrecv")
        rx = make("rtprtxreceive", "artxrecv")
        rx.set_property("payload-type-map", pt_map_struct(111, 112))
        box.add(rx)
        box.add_pad(Gst.GhostPad.new("sink_1", rx.get_static_pad("sink")))
        box.add_pad(Gst.GhostPad.new("src_1", rx.get_static_pad("src")))
        return box
    rtpbin.connect("request-aux-receiver", aux_receiver)

    def pad_added(b, pad):
        n = pad.get_name()
        stats.setdefault("pad_added", []).append(n)
        # rtpbin templates: send_rtp_src_%u and recv_rtp_src_%u_%u_%u
        if n.startswith("recv_rtp_src_0_"):
            pad.link(vdepay.get_static_pad("sink"))
            probe_rtp_pt(pad, stats, "in_video")
        elif n.startswith("recv_rtp_src_1_"):
            pad.link(adepay.get_static_pad("sink"))
            probe_rtp_pt(pad, stats, "in_audio")
        elif n.startswith("send_rtcp_src_0"):
            pass
        elif n.startswith("send_rtcp_src_1"):
            pass
    rtpbin.connect("pad-added", pad_added)

    v_src.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtp_sink_0"))
    a_src.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtp_sink_1"))
    fb0 = rtpbin.request_pad_simple("recv_rtcp_sink_0")
    fb1 = rtpbin.request_pad_simple("recv_rtcp_sink_1")
    v_rtcp_src.get_static_pad("src").link(fb0)
    a_rtcp_src.get_static_pad("src").link(fb1)
    # SR records are what the receiver sees; needed for the NTP<->RTP mapping check.
    probe_sr(fb0, stats, "sr_in_video")
    probe_sr(fb1, stats, "sr_in_audio")
    for sess, sink in ((0, v_rtcp_sink), (1, a_rtcp_sink)):
        pad = rtpbin.request_pad_simple("send_rtcp_src_%u" % sess)
        if pad is not None:
            pad.link(sink.get_static_pad("sink"))
            probe_rtcp_pt(pad, stats, "rtcp_out%d" % sess)
    vdepay.link(vparse)
    vparse.link(vdec)
    vdec.link(vconv)
    vconv.link(vscale)
    vscale.link(vcap)
    vcap.link(vsink)
    adepay.link(adec)
    adec.link(aconv)
    aconv.link(ares)
    ares.link(acap)
    acap.link(asink)
    probe_count(vcap.get_static_pad("src"), stats, "video_frames")
    probe_count(acap.get_static_pad("src"), stats, "audio_buffers")
    probe_rtp_pt(a_src.get_static_pad("src"), stats, "net_audio")
    probe_rtp_ssrc(v_src.get_static_pad("src"), stats)
    HOLDER["vdepay"] = vdepay
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["sender", "receiver"])
    ap.add_argument("--file", default="/home/bai/rtc_test/anchor.mkv")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--video-rtp-port", type=int, default=5004)
    ap.add_argument("--video-rtcp-port", type=int, default=5006)
    ap.add_argument("--video-feedback-port", type=int, default=5005)
    ap.add_argument("--audio-rtp-port", type=int, default=5008)
    ap.add_argument("--audio-rtcp-port", type=int, default=5010)
    ap.add_argument("--audio-feedback-port", type=int, default=5009)
    ap.add_argument("--latency", type=int, default=500)
    ap.add_argument("--seconds", type=float, default=16.0)
    ap.add_argument("--video-out", default="/tmp/t8_video.yuv")
    ap.add_argument("--audio-out", default="/tmp/t8_audio.pcm")
    ap.add_argument("--synthetic", action="store_true",
                    help="sender: use videotestsrc/audiotestsrc (for long SR runs)")
    ap.add_argument("--audio-loss", type=float, default=0.0,
                    help="sender: drop probability on the audio RTP path")
    ap.add_argument("--no-audio-rtx", action="store_true",
                    help="receiver: disable retransmission handling for audio")
    ap.add_argument("--video-loss", type=float, default=0.0,
                    help="sender: drop probability on the video RTP path")
    ap.add_argument("--force-keyframe", action="store_true",
                    help="receiver: ask the depayloader to request keyframes on loss")
    ap.add_argument("--inject-pli", action="store_true",
                    help="receiver: inject a GstForceKeyUnit upstream event at 5s")
    ap.add_argument("--bind-address", default="",
                    help="sender: local source address (forces the media interface)")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=180)
    a = ap.parse_args()

    stats = {}
    if a.role == "sender":
        p = build_sender(a, stats)
    else:
        p = build_receiver(a, stats)

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
    GLib.timeout_add(int((a.seconds + 6) * 1000), lambda: (loop.quit(), False)[1])

    def inject_pli():
        ssrc = stats.get("video_ssrc")
        depay = HOLDER.get("vdepay")
        if ssrc is None or depay is None:
            stats["pli_inject_err"] = "no ssrc or depay"
            return False
        try:
            st = Gst.Structure.new_empty("GstForceKeyUnit")
            v = GObject.Value()
            v.init(GObject.TYPE_UINT)
            v.set_uint(int(ssrc))
            st.set_value("ssrc", v)
            v2 = GObject.Value()
            v2.init(GObject.TYPE_UINT)
            v2.set_uint(96)
            st.set_value("payload", v2)
            ev = Gst.Event.new_custom(Gst.EventType.CUSTOM_UPSTREAM, st)
            ok1 = bool(depay.get_static_pad("sink").push_event(ev))
            ev2 = Gst.Event.new_custom(Gst.EventType.CUSTOM_UPSTREAM, st.copy())
            ok2 = bool(depay.send_event(ev2))
            stats["pli_push_ok"] = int(ok1)
            stats["pli_send_ok"] = int(ok2)
        except Exception as exc:
            stats["pli_inject_err"] = str(exc)
        return False

    if a.role == "receiver" and a.inject_pli:
        GLib.timeout_add(5000, inject_pli)

    loop.run()
    p.set_state(Gst.State.NULL)

    if a.role == "receiver":
        for key, jb in HOLDER.items():
            try:
                st = jb.get_property("stats")
                d = {}
                for i in range(st.n_fields()):
                    nm = st.nth_field_name(i)
                    d[nm] = st.get_value(nm)
                stats[key] = d
            except Exception as exc:
                stats[key + "_err"] = str(exc)

    for key in ("sr_video", "sr_audio"):
        if key in stats:
            stats[key] = stats[key][:4]
    print("RESULT " + json.dumps({"role": a.role, "stats": stats}, default=str), flush=True)
    import os
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
