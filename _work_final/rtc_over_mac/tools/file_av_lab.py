#!/usr/bin/env python3
"""File-based dual-stream RTP/RTX/SRTP/PLI retest on GStreamer/rtpbin.

Designed for the six Pi MP4 test clips. The sender demuxes H264 + AAC; audio
is decoded, resampled and encoded to Opus. Video is passed through H264 parse/pay
by default; --reencode-video decodes/rescales/encodes through openh264enc so the
sender can honor upstream keyframe requests (needed for a valid PLI round trip).

Roles run separately on 127.0.0.1 or over the configured host. Prints one RESULT
JSON line. Counters are sampled while PLAYING because rtprtxsend/receiver reset
on NULL.
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
TEST_KEY = bytes(range(30))
PT_NAMES = {200: "SR", 201: "RR", 205: "NACK", 206: "PLI"}


def make(factory, name):
    el = Gst.ElementFactory.make(factory, name)
    if el is None:
        raise RuntimeError("missing element: %s" % factory)
    return el


def caps(s):
    return Gst.Caps.from_string(s)


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


def pt_map_struct(pt, rtx_pt):
    res = Gst.Structure.from_string("application/x-rtp-pt-map,%d=(uint)%d" % (pt, rtx_pt))
    for item in res:
        if isinstance(item, Gst.Structure):
            return item
    raise RuntimeError("bad pt map")


def probe_count(pad, stats, key):
    def cb(p, info):
        stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_audio_samples(pad, stats):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            stats["audio_buffers"] = stats.get("audio_buffers", 0) + 1
            stats["audio_samples"] = stats.get("audio_samples", 0) + buf.get_size() // 2
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def rtp_pt(buf):
    try:
        data = bytes(buf.extract_dup(0, min(buf.get_size(), 16)))
    except Exception:
        return None
    if len(data) >= 2 and (data[0] >> 6) == 2:
        return data[1] & 0x7F
    return None


def probe_rtp_pt(pad, stats, prefix):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            pt = rtp_pt(buf)
            if pt is not None:
                stats["%s_pt%d" % (prefix, pt)] = stats.get("%s_pt%d" % (prefix, pt), 0) + 1
                try:
                    data = bytes(buf.extract_dup(0, 12))
                    if len(data) >= 12 and "ssrc" not in stats:
                        stats["ssrc"] = struct.unpack("!I", data[8:12])[0]
                except Exception:
                    pass
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def parse_rtcp_sr(buf):
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
            out.append({
                "ssrc": struct.unpack("!I", data[i + 4:i + 8])[0],
                "ntp": struct.unpack("!Q", data[i + 8:i + 16])[0],
                "rtp_ts": struct.unpack("!I", data[i + 16:i + 20])[0],
            })
        if ln <= 0:
            break
        i += ln
    return out


def probe_sr(pad, stats, key):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            for rec in parse_rtcp_sr(buf):
                stats.setdefault(key, []).append(rec)
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


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
            k = "%s_%s" % (prefix, PT_NAMES.get(pt, str(pt)))
            stats[k] = stats.get(k, 0) + 1
            if ln <= 0:
                break
            i += ln
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def fk_enricher(stats, ssrc, pt):
    def cb(p, info):
        ev = None
        try:
            ev = info.get_event()
        except Exception:
            ev = getattr(info, "event", None)
        if ev is not None and ev.type == Gst.EventType.CUSTOM_UPSTREAM:
            try:
                st = ev.writable_structure()
            except Exception:
                st = ev.get_structure()
            if st is not None and st.get_name() == "GstForceKeyUnit":
                try:
                    if not st.has_field("ssrc"):
                        v = GObject.Value(); v.init(GObject.TYPE_UINT); v.set_uint(ssrc)
                        st.set_value("ssrc", v)
                    if not st.has_field("payload"):
                        v = GObject.Value(); v.init(GObject.TYPE_UINT); v.set_uint(pt)
                        st.set_value("payload", v)
                    stats["fk_enriched"] = stats.get("fk_enriched", 0) + 1
                except Exception as exc:
                    stats["fk_enrich_err"] = str(exc)
        return Gst.PadProbeReturn.OK
    return cb


def count_idr(data):
    off = 0
    while off + 5 <= len(data):
        ln = int.from_bytes(data[off:off + 4], "big")
        if ln <= 0 or off + 4 + ln > len(data):
            break
        if (data[off + 4] & 0x1F) == 5:
            return 1
        off += 4 + ln
    i = data.find(b"\x00\x00\x01")
    while i >= 0 and i + 3 < len(data):
        if (data[i + 3] & 0x1F) == 5:
            return 1
        i = data.find(b"\x00\x00\x01", i + 3)
    return 0


def probe_idr(pad, stats):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            try:
                data = bytes(buf.extract_dup(0, buf.get_size()))
                if count_idr(data):
                    stats["idr_aus"] = stats.get("idr_aus", 0) + 1
                    stats.setdefault("idr_times", []).append(GLib.get_monotonic_time() / 1e6)
            except Exception:
                pass
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_keyframe_event(pad, stats, tag):
    def cb(p, info):
        ev = None
        try:
            ev = info.get_event()
        except Exception:
            ev = getattr(info, "event", None)
        if ev is not None:
            st = None
            try:
                st = ev.get_structure()
            except Exception:
                st = None
            if st is not None and st.get_name() == "GstForceKeyUnit":
                stats[tag] = stats.get(tag, 0) + 1
                stats.setdefault("keyframe_event_times", []).append(
                    GLib.get_monotonic_time() / 1e6)
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, cb)


VIDEO_CAPS = ("application/x-rtp,media=video,encoding-name=H264,payload=96,"
              "clock-rate=90000,rtcp-fb-nack=(boolean)true,rtcp-fb-nack-pli=(boolean)true")
AUDIO_CAPS = ("application/x-rtp,media=audio,encoding-name=OPUS,payload=111,"
              "clock-rate=48000,rtcp-fb-nack=(boolean)true")
RTX_VIDEO = "application/x-rtp,media=video,encoding-name=rtx,payload=97,clock-rate=90000"
RTX_AUDIO = "application/x-rtp,media=audio,encoding-name=rtx,payload=112,clock-rate=48000"


def pt_map_cb(bin, session, pt, a, stats):
    if session == 0 and pt == 96:
        return caps(VIDEO_CAPS)
    if session == 0 and pt == 97 and a.video_rtx:
        return caps(RTX_VIDEO)
    if session == 1 and pt == 111:
        return caps(AUDIO_CAPS)
    if session == 1 and pt == 112 and a.audio_rtx:
        return caps(RTX_AUDIO)
    return None


def aux_bin_factory(session, rtx_pt, map_pt, rx=False):
    box = Gst.Bin.new("rtx-%s-%d" % ("recv" if rx else "send", session))
    el = make("rtprtxreceive" if rx else "rtprtxsend",
              "rtxrecv%d" % session if rx else "rtxsend%d" % session)
    el.set_property("payload-type-map", pt_map_struct(map_pt, rtx_pt))
    if not rx:
        # T7 frozen parameters: the default 100-packet history drops the
        # packet long before the NACK arrives.
        el.set_property("max-size-packets", 5000)
        el.set_property("max-size-time", 5000)
    box.add(el)
    box.add_pad(Gst.GhostPad.new("sink_%d" % session, el.get_static_pad("sink")))
    box.add_pad(Gst.GhostPad.new("src_%d" % session, el.get_static_pad("src")))
    return box, el


def apply_session_props(rtpbin, stats, session):
    """Apply the frozen T7 RTCP parameters to one rtpbin session.

    rtpbin has no new-session signal; get-session returns the rtpsession
    element once the corresponding sink pad has been requested.
    """
    try:
        el = rtpbin.emit("get-session", session)
    except Exception as exc:
        stats["session_err_%d" % session] = str(exc)
        return
    if el is None:
        stats["session_none_%d" % session] = True
        return
    try:
        el.set_property("bandwidth", 1000000.0)
        el.set_property("rtcp-min-interval", 100000000)
        el.set_property("rtp-profile", 3)
        stats.setdefault("session_props", []).append(int(session))
    except Exception as exc:
        stats["session_prop_err_%d" % session] = str(exc)


def build_sender(a, stats):
    p = Gst.Pipeline.new("file-av-sender")
    rtpbin = make("rtpbin", "rtpbin")
    rtpbin.set_property("latency", a.latency)
    rtpbin.set_property("do-retransmission", a.video_rtx or a.audio_rtx)
    rtpbin.set_property("rtp-profile", 3)

    src = make("filesrc", "src"); src.set_property("location", a.file)
    demux = make("qtdemux", "demux")
    vparse = make("h264parse", "vparse")
    vpay = make("rtph264pay", "vpay"); vpay.set_property("pt", 96); vpay.set_property("config-interval", 1)
    apay = make("rtpopuspay", "apay"); apay.set_property("pt", 111)
    venc = None
    if a.reencode_video:
        vdec = make("avdec_h264", "vdec")
        vconv = make("videoconvert", "vconv")
        vscale = make("videoscale", "vscale")
        vcap = make("capsfilter", "vcap")
        vcap.set_property("caps", caps("video/x-raw,width=%d,height=%d" % (a.width, a.height)))
        venc = make("openh264enc", "venc"); venc.set_property("bitrate", 2000000)
        for el in (vdec, vconv, vscale, vcap, venc): p.add(el)
    adev = make("avdec_aac", "adev")
    aconv = make("audioconvert", "aconv")
    ares = make("audioresample", "ares")
    acap = make("capsfilter", "acap")
    acap.set_property("caps", caps("audio/x-raw,format=S16LE,channels=1,rate=48000"))
    aenc = make("opusenc", "aenc")

    v_drop = make("identity", "v_drop"); v_drop.set_property("drop-probability", a.video_loss)
    a_drop = make("identity", "a_drop"); a_drop.set_property("drop-probability", a.audio_loss)
    v_sink = make("udpsink", "v_sink"); v_sink.set_property("host", a.host); v_sink.set_property("port", a.video_rtp_port)
    a_sink = make("udpsink", "a_sink"); a_sink.set_property("host", a.host); a_sink.set_property("port", a.audio_rtp_port)
    v_rtcp = make("udpsink", "v_rtcp"); v_rtcp.set_property("host", a.host); v_rtcp.set_property("port", a.video_rtcp_port)
    a_rtcp = make("udpsink", "a_rtcp"); a_rtcp.set_property("host", a.host); a_rtcp.set_property("port", a.audio_rtcp_port)
    v_fb = make("udpsrc", "v_fb"); v_fb.set_property("port", a.video_feedback_port); v_fb.set_property("caps", caps("application/x-rtcp"))
    a_fb = make("udpsrc", "a_fb"); a_fb.set_property("port", a.audio_feedback_port); a_fb.set_property("caps", caps("application/x-rtcp"))
    for s in (v_sink, a_sink, v_rtcp, a_rtcp):
        s.set_property("sync", bool(a.pace and s in (v_sink, a_sink))); s.set_property("async", False)

    srtp_enc = {}
    srtp_sink_pads = {}
    if a.srtp:
        # The srtpenc src pads are linked to the drop elements right away, so
        # both sides must already belong to the pipeline (else wrong-hierarchy).
        p.add(v_drop)
        p.add(a_drop)
        for sess in (0, 1):
            enc = make("srtpenc", "srtpenc%d" % sess)
            enc.set_property("key", Gst.Buffer.new_wrapped(TEST_KEY))
            p.add(enc)

            def _on_src(e, pad, sess=sess):
                # rtp_src_%u is a SOMETIMES pad; it only exists once the sink
                # side is active, so the handler must be connected first.
                stats.setdefault("srtp_src_added", []).append(pad.get_name())
                target = v_drop if sess == 0 else a_drop
                try:
                    stats["srtp_src_link_%d" % sess] = pad.link(
                        target.get_static_pad("sink")).value_nick
                except Exception as exc:
                    stats["srtp_src_link_err_%d" % sess] = str(exc)

            enc.connect("pad-added", _on_src)
            srtp_enc[sess] = enc
            srtp_sink_pads[sess] = enc.request_pad_simple("rtp_sink_%d" % sess)
            encsrc = enc.get_static_pad("rtp_src_%d" % sess)
            if encsrc is not None and not encsrc.is_linked():
                target = v_drop if sess == 0 else a_drop
                stats["srtp_src_link_%d" % sess] = encsrc.link(
                    target.get_static_pad("sink")).value_nick

    for el in (src, demux, vparse, vpay, apay, adev, aconv, ares, acap, aenc,
               rtpbin, v_drop, a_drop, v_sink, a_sink, v_rtcp, a_rtcp, v_fb, a_fb):
        p.add(el)

    src.link(demux)

    def demux_pad(b, pad):
        name = pad.get_name()
        if name.startswith("video"):
            if a.reencode_video:
                pad.link(vdec.get_static_pad("sink")); vdec.link(vconv); vconv.link(vscale); vscale.link(vcap); vcap.link(venc); venc.link(vparse)
            else:
                pad.link(vparse.get_static_pad("sink"))
        elif name.startswith("audio"):
            pad.link(adev.get_static_pad("sink")); adev.link(aconv); aconv.link(ares); ares.link(acap); acap.link(aenc); aenc.link(apay)
    demux.connect("pad-added", demux_pad)
    vparse.link(vpay); aenc.link(apay)

    if a.reencode_video:
        probe_keyframe_event(venc.get_static_pad("sink"), stats, "keyframe_events_encoder_sink")
        probe_keyframe_event(venc.get_static_pad("src"), stats, "keyframe_events_encoder_src")
        probe_idr(vparse.get_static_pad("src"), stats)

    rtpbin.connect("request-pt-map", lambda b, s, pt: pt_map_cb(b, s, pt, a, stats))

    def aux_sender(b, session):
        if session == 0 and a.video_rtx:
            box, el = aux_bin_factory(0, 97, 96, False); HOLDER["tx0"] = el; return box
        if session == 1 and a.audio_rtx:
            box, el = aux_bin_factory(1, 112, 111, False); HOLDER["tx1"] = el; return box
        return None
    rtpbin.connect("request-aux-sender", aux_sender)

    def pad_added(b, pad):
        n = pad.get_name(); stats.setdefault("pad_added", []).append(n)
        if n.startswith("send_rtp_src_0"):
            if a.srtp:
                ret = pad.link(srtp_sink_pads[0]); stats["link_v_srtp"] = ret.value_nick
            else:
                pad.link(v_drop.get_static_pad("sink"))
        elif n.startswith("send_rtp_src_1"):
            if a.srtp:
                ret = pad.link(srtp_sink_pads[1]); stats["link_a_srtp"] = ret.value_nick
            else:
                pad.link(a_drop.get_static_pad("sink"))
    rtpbin.connect("pad-added", pad_added)

    v_drop.link(v_sink); a_drop.link(a_sink)
    vpay.get_static_pad("src").link(rtpbin.request_pad_simple("send_rtp_sink_0"))
    apay.get_static_pad("src").link(rtpbin.request_pad_simple("send_rtp_sink_1"))
    apply_session_props(rtpbin, stats, 0)
    apply_session_props(rtpbin, stats, 1)
    v_fb.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtcp_sink_0"))
    a_fb.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtcp_sink_1"))
    probe_rtcp_pt(v_fb.get_static_pad("src"), stats, "rtcp_in_video")
    probe_rtcp_pt(a_fb.get_static_pad("src"), stats, "rtcp_in_audio")
    for sess, sink, key in ((0, v_rtcp, "sr_video"), (1, a_rtcp, "sr_audio")):
        pad = rtpbin.request_pad_simple("send_rtcp_src_%u" % sess)
        pad.link(sink.get_static_pad("sink")); probe_sr(pad, stats, key)
    return p


def on_request_key(elem, ssrc, udata):
    caps_out = Gst.Caps.from_string(
        "application/x-srtp,srtp-cipher=(string)aes-128-icm,srtp-auth=(string)hmac-sha1-80,"
        "srtcp-cipher=(string)aes-128-icm,srtcp-auth=(string)hmac-sha1-80")
    caps_out.set_value("srtp-key", Gst.Buffer.new_wrapped(TEST_KEY))
    return caps_out


def build_receiver(a, stats):
    p = Gst.Pipeline.new("file-av-receiver")
    rtpbin = make("rtpbin", "rtpbin"); rtpbin.set_property("latency", a.latency)
    rtpbin.set_property("do-retransmission", a.video_rtx or a.audio_rtx)
    if a.force_keyframe:
        rtpbin.set_property("do-lost", True)
    rtpbin.set_property("rtp-profile", 3)
    v_src = make("udpsrc", "v_src"); v_src.set_property("port", a.video_rtp_port); v_src.set_property("buffer-size", 8 * 1024 * 1024)
    a_src = make("udpsrc", "a_src"); a_src.set_property("port", a.audio_rtp_port); a_src.set_property("buffer-size", 8 * 1024 * 1024)
    v_rtcp_src = make("udpsrc", "v_rtcp_src"); v_rtcp_src.set_property("port", a.video_rtcp_port); v_rtcp_src.set_property("caps", caps("application/x-rtcp"))
    a_rtcp_src = make("udpsrc", "a_rtcp_src"); a_rtcp_src.set_property("port", a.audio_rtcp_port); a_rtcp_src.set_property("caps", caps("application/x-rtcp"))
    v_rtcp_sink = make("udpsink", "v_rtcp_sink"); v_rtcp_sink.set_property("host", a.host); v_rtcp_sink.set_property("port", a.video_feedback_port)
    a_rtcp_sink = make("udpsink", "a_rtcp_sink"); a_rtcp_sink.set_property("host", a.host); a_rtcp_sink.set_property("port", a.audio_feedback_port)
    for s in (v_rtcp_sink, a_rtcp_sink): s.set_property("sync", False); s.set_property("async", False)

    srtp_dec = {}
    if a.srtp:
        for sess in (0, 1):
            dec = make("srtpdec", "srtpdec%d" % sess)
            dec.connect("request-key", on_request_key, None)
            p.add(dec); srtp_dec[sess] = dec

    vdepay = make("rtph264depay", "vdepay")
    if a.force_keyframe:
        vdepay.set_property("request-keyframe", True)
    vparse = make("h264parse", "vparse"); vdec = make("avdec_h264", "vdec"); vsink = make("fakesink", "vsink")
    adepay = make("rtpopusdepay", "adepay"); adec = make("opusdec", "adec"); aconv = make("audioconvert", "aconv")
    ares = make("audioresample", "ares"); acap = make("capsfilter", "acap")
    acap.set_property("caps", caps("audio/x-raw,format=S16LE,channels=1,rate=48000")); asink = make("fakesink", "asink")

    for el in (v_src, a_src, v_rtcp_src, a_rtcp_src, v_rtcp_sink, a_rtcp_sink, rtpbin,
               vdepay, vparse, vdec, vsink, adepay, adec, aconv, ares, acap, asink):
        p.add(el)

    v_src.set_property("caps", caps("application/x-srtp,media=video,clock-rate=90000" if a.srtp else VIDEO_CAPS))
    a_src.set_property("caps", caps("application/x-srtp,media=audio,clock-rate=48000" if a.srtp else AUDIO_CAPS))

    rtpbin.connect("request-pt-map", lambda b, s, pt: pt_map_cb(b, s, pt, a, stats))

    def aux_receiver(b, session):
        if session == 0 and a.video_rtx:
            box, el = aux_bin_factory(0, 97, 96, True); HOLDER["rx0"] = el; return box
        if session == 1 and a.audio_rtx:
            box, el = aux_bin_factory(1, 112, 111, True); HOLDER["rx1"] = el; return box
        return None
    rtpbin.connect("request-aux-receiver", aux_receiver)

    def new_jb(b, jb, session, pt):
        HOLDER.setdefault("jbs", []).append((session, pt, jb))
    rtpbin.connect("new-jitterbuffer", new_jb)

    def pad_added(b, pad):
        n = pad.get_name(); stats.setdefault("pad_added", []).append(n)
        if n.startswith("recv_rtp_src_0_"):
            pad.link(vdepay.get_static_pad("sink")); probe_rtp_pt(pad, stats, "in_video")
            parts = n.split("_")
            if len(parts) >= 6:
                try:
                    ssrc, pt = int(parts[4]), int(parts[5])
                    pad.add_probe(Gst.PadProbeType.EVENT_UPSTREAM, fk_enricher(stats, ssrc, pt))
                except ValueError:
                    pass
        elif n.startswith("recv_rtp_src_1_"):
            pad.link(adepay.get_static_pad("sink")); probe_rtp_pt(pad, stats, "in_audio")
    rtpbin.connect("pad-added", pad_added)

    def link_rtp(sess, src_el):
        if a.srtp:
            src_el.get_static_pad("src").link(srtp_dec[sess].get_static_pad("rtp_sink"))
            srtp_dec[sess].get_static_pad("rtp_src").link(rtpbin.request_pad_simple("recv_rtp_sink_%d" % sess))
        else:
            src_el.get_static_pad("src").link(rtpbin.request_pad_simple("recv_rtp_sink_%d" % sess))
    link_rtp(0, v_src); link_rtp(1, a_src)
    apply_session_props(rtpbin, stats, 0)
    apply_session_props(rtpbin, stats, 1)
    fb0 = rtpbin.request_pad_simple("recv_rtcp_sink_0"); fb1 = rtpbin.request_pad_simple("recv_rtcp_sink_1")
    v_rtcp_src.get_static_pad("src").link(fb0); a_rtcp_src.get_static_pad("src").link(fb1)
    probe_sr(fb0, stats, "sr_in_video"); probe_sr(fb1, stats, "sr_in_audio")
    pad0 = rtpbin.request_pad_simple("send_rtcp_src_0"); pad0.link(v_rtcp_sink.get_static_pad("sink")); probe_rtcp_pt(pad0, stats, "rtcp_out0")
    pad1 = rtpbin.request_pad_simple("send_rtcp_src_1"); pad1.link(a_rtcp_sink.get_static_pad("sink")); probe_rtcp_pt(pad1, stats, "rtcp_out1")

    vdepay.link(vparse); vparse.link(vdec); vdec.link(vsink)
    adepay.link(adec); adec.link(aconv); aconv.link(ares); ares.link(acap); acap.link(asink)
    probe_count(vdec.get_static_pad("src"), stats, "video_frames")
    probe_audio_samples(acap.get_static_pad("src"), stats)
    probe_rtp_pt(v_src.get_static_pad("src"), stats, "net_video")
    probe_rtp_pt(a_src.get_static_pad("src"), stats, "net_audio")
    return p


def collect_element_stats(el):
    out = {}
    for prop in ("num-rtx-requests", "num-rtx-packets", "num-rtx-assoc-packets"):
        try:
            out[prop] = el.get_property(prop)
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["sender", "receiver"])
    ap.add_argument("--file", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--video-rtp-port", type=int, default=5004)
    ap.add_argument("--video-rtcp-port", type=int, default=5006)
    ap.add_argument("--video-feedback-port", type=int, default=5005)
    ap.add_argument("--audio-rtp-port", type=int, default=5008)
    ap.add_argument("--audio-rtcp-port", type=int, default=5010)
    ap.add_argument("--audio-feedback-port", type=int, default=5009)
    ap.add_argument("--latency", type=int, default=500)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--video-loss", type=float, default=0.0)
    ap.add_argument("--audio-loss", type=float, default=0.0)
    ap.add_argument("--video-rtx", action="store_true")
    ap.add_argument("--audio-rtx", action="store_true")
    ap.add_argument("--srtp", action="store_true")
    ap.add_argument("--reencode-video", action="store_true")
    ap.add_argument("--pace", action="store_true",
                    help="sender: pace RTP output to real time (udpsink sync)")
    ap.add_argument("--force-keyframe", action="store_true")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--height", type=int, default=180)
    a = ap.parse_args()

    stats = {"args": vars(a)}
    p = build_sender(a, stats) if a.role == "sender" else build_receiver(a, stats)
    loop = GLib.MainLoop()
    errors = []

    def on_msg(bus, msg):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error(); errors.append(err.message + " | " + dbg); loop.quit()
        elif msg.type == Gst.MessageType.EOS:
            loop.quit()
        elif msg.type == Gst.MessageType.WARNING:
            err, _ = msg.parse_warning(); errors.append("WARN: " + err.message)
    bus = p.get_bus(); bus.add_signal_watch(); bus.connect("message", on_msg)

    if p.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        print("RESULT " + json.dumps({"ok": False, "errors": ["state failure"]}, default=str)); return 2

    def sample():
        for tag in ("tx0", "tx1", "rx0", "rx1"):
            el = HOLDER.get(tag)
            if el is not None:
                stats[tag + "_mid"] = collect_element_stats(el)
        jbs = HOLDER.get("jbs", [])
        for i, (sess, pt, jb) in enumerate(jbs):
            try:
                st = jb.get_property("stats"); d = {}
                for k in range(st.n_fields()):
                    nm = st.nth_field_name(k); d[nm] = st.get_value(nm)
                stats["jb_%d_%s" % (sess, pt)] = d
            except Exception as exc:
                stats["jb_err_%d" % i] = str(exc)
        return True
    GLib.timeout_add(1000, sample)

    def stop():
        try: p.send_event(Gst.Event.new_eos())
        except Exception: pass
        return False
    GLib.timeout_add(int(a.seconds * 1000), stop)
    GLib.timeout_add(int((a.seconds + 6) * 1000), lambda: (loop.quit(), False)[1])
    loop.run()
    p.set_state(Gst.State.NULL)

    for tag in ("tx0", "tx1", "rx0", "rx1"):
        el = HOLDER.get(tag)
        if el is not None:
            stats[tag + "_after_null"] = collect_element_stats(el)
    stats["errors"] = errors
    for key in ("sr_video", "sr_audio", "sr_in_video", "sr_in_audio"):
        if key in stats:
            stats[key] = stats[key][:4]
    if "idr_times" in stats and "keyframe_event_times" in stats:
        events = stats["keyframe_event_times"]; idrs = stats["idr_times"]
        near = 0
        for t in idrs:
            if any(0 <= t - e <= 0.5 for e in events):
                near += 1
        stats["idrs_within_500ms_after_event"] = near
    print("RESULT " + json.dumps({"role": a.role, "stats": stats}, default=str), flush=True)
    import os; os._exit(0)


if __name__ == "__main__":
    sys.exit(main())



