#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
srtp_loopback.py — T4 SRTP 加解密本地回环闭环（PyGI 代码级管线）

为什么需要代码级管线：
  srtpdec 的密钥只能经 request-key 信号回调提供，gst-launch 无法连接回调，
  因此用 Python GStreamer 绑定搭建发送/接收两条管线。

链路：
  发送：filesrc ! qtdemux ! h264parse ! rtph264pay ! srtpenc(密钥) ! udpsink
  接收：udpsrc(x-srtp) ! srtpdec(request-key 供钥) ! rtph264depay ! h264parse ! avdec ! fakesink

校验：
  - srtpdec stats: recv-count（成功解密包数）、recv-drop-count（鉴权/解密失败丢弃数）
  - srtpenc stats: 发送包数
  - 解码侧探针计数缓冲帧数
  - 全程总线无 ERROR/WARNING 致命错误
"""

import gi
import json
import time

gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)

# 测试固定密钥：SRTP AES-128 主密钥 16 字节 + master salt 14 字节 = 30 字节
# 仅用于本地回环自测，生产环境由 DTLS/PSK 协商产生
TEST_KEY = bytes(range(30))
CLIP = "/home/bai/rtc_test/clip10.mp4"
PORT = 5050

frame_count = {"n": 0}


def on_request_key(elem, ssrc, udata):
    """srtpdec request-key 信号回调：按 SSRC 返回该流的 SRTP 参数 caps。"""
    caps = Gst.Caps.from_string(
        "application/x-srtp,"
        "srtp-cipher=(string)aes-128-icm,"
        "srtp-auth=(string)hmac-sha1-80,"
        "srtcp-cipher=(string)aes-128-icm,"
        "srtcp-auth=(string)hmac-sha1-80"
    )
    caps.set_value("srtp-key", Gst.Buffer.new_wrapped(TEST_KEY))
    print("[request-key] ssrc=%u 提供密钥" % ssrc)
    return caps


def make_element(factory, name):
    e = Gst.ElementFactory.make(factory, name)
    if e is None:
        raise SystemExit("缺少元件: %s" % factory)
    return e


def link_or_fail(src, dst):
    if not src.link(dst):
        raise SystemExit("链接失败: %s -> %s" % (src.get_name(), dst.get_name()))


def build_sender():
    pipe = Gst.Pipeline.new("srtp-sender")
    src = make_element("filesrc", "src")
    src.set_property("location", CLIP)
    demux = make_element("qtdemux", "demux")
    parse = make_element("h264parse", "parse")
    pay = make_element("rtph264pay", "pay")
    pay.set_property("pt", 96)
    pay.set_property("config-interval", 1)
    enc = make_element("srtpenc", "enc")
    enc.set_property("key", Gst.Buffer.new_wrapped(TEST_KEY))
    sink = make_element("udpsink", "sink")
    sink.set_property("host", "127.0.0.1")
    sink.set_property("port", PORT)
    pipe.add(src); pipe.add(demux); pipe.add(parse); pipe.add(pay)
    pipe.add(enc); pipe.add(sink)
    link_or_fail(src, demux)

    # qtdemux 的视频 pad 是有时才出现（sometimes），必须等 pad-added 再挂接
    def on_pad_added(dmx, pad, target):
        if pad.get_name().startswith("video"):
            pad.link(target.get_static_pad("sink"))

    demux.connect("pad-added", on_pad_added, parse)
    link_or_fail(parse, pay)
    link_or_fail(pay, enc)
    link_or_fail(enc, sink)
    return pipe, enc


def on_frame_probe(pad, info, udata):
    frame_count["n"] += 1
    return Gst.PadProbeReturn.OK


def build_receiver():
    pipe = Gst.Pipeline.new("srtp-receiver")
    src = make_element("udpsrc", "src")
    src.set_property("port", PORT)
    src.set_property("caps", Gst.Caps.from_string(
        "application/x-srtp, media=(string)video, clock-rate=(int)90000,"
        " encoding-name=(string)H264, payload=(int)96"))
    dec = make_element("srtpdec", "dec")
    dec.connect("request-key", on_request_key, None)
    depay = make_element("rtph264depay", "depay")
    parse = make_element("h264parse", "parse")
    avdec = make_element("avdec_h264", "avdec")
    sink = make_element("fakesink", "sink")
    pipe.add(src); pipe.add(dec); pipe.add(depay); pipe.add(parse)
    pipe.add(avdec); pipe.add(sink)
    link_or_fail(src, dec); link_or_fail(dec, depay); link_or_fail(depay, parse)
    link_or_fail(parse, avdec); link_or_fail(avdec, sink)
    avdec.get_static_pad("src").add_probe(Gst.PadProbeType.BUFFER, on_frame_probe, None)
    return pipe, dec


def stats_of(elem):
    st = elem.get_property("stats")
    if not st:
        return {}
    return {"raw": st.to_string()}


def main():
    sender, enc = build_sender()
    receiver, dec = build_receiver()

    errors = []
    for pipe, tag in ((sender, "sender"), (receiver, "receiver")):
        bus = pipe.get_bus()
        bus.add_signal_watch()

        def on_msg(bus, msg, tag=tag):
            if msg.type == Gst.MessageType.ERROR:
                errors.append("%s ERROR: %s" % (tag, msg.parse_error()[1].message))
            elif msg.type == Gst.MessageType.WARNING:
                errors.append("%s WARN: %s" % (tag, msg.parse_warning()[1].message))

        bus.connect("message", on_msg)

    receiver.set_state(Gst.State.PLAYING)
    time.sleep(1)
    sender.set_state(Gst.State.PLAYING)
    time.sleep(12)

    result = {
        "sender_stats": stats_of(enc),
        "receiver_stats": stats_of(dec),
        "decoded_frames": frame_count["n"],
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, default=str))

    sender.set_state(Gst.State.NULL)
    receiver.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
