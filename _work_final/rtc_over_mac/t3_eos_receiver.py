#!/usr/bin/env python3
"""T3/T4-style UDP receiver with explicit EOS to flush the decoder tail."""
import argparse
import os
import sys

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

Gst.init(None)


def wait_eos(bus, timeout_ns):
    msg = bus.timed_pop_filtered(timeout_ns, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    if msg is None:
        return "timeout"
    if msg.type == Gst.MessageType.ERROR:
        err, dbg = msg.parse_error()
        print("ERROR", err.message, dbg, flush=True)
        return "error"
    return "eos"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default="/home/bai/rtc_test/clip10.mp4")
    ap.add_argument("--out", default="/tmp/t3_rx.yuv")
    ap.add_argument("--port", type=int, default=5024)
    args = ap.parse_args()

    rx = Gst.parse_launch(
        f"udpsrc port={args.port} caps=application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000 "
        "! rtpjitterbuffer latency=200 ! rtph264depay ! h264parse ! avdec_h264 "
        f"! videoconvert ! videoscale ! video/x-raw,format=I420,width=320,height=180 ! filesink sync=false location={args.out}"
    )
    tx = Gst.parse_launch(
        f"filesrc location={args.clip} ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host=127.0.0.1 port={args.port} sync=true"
    )

    rx.set_state(Gst.State.PLAYING)
    tx.set_state(Gst.State.PLAYING)

    print("sender waiting EOS", flush=True)
    tx_rc = wait_eos(tx.get_bus(), 30 * Gst.SECOND)
    print("sender", tx_rc, flush=True)

    # UDP carries no EOS; inject one into the receiver so avdec flushes its tail.
    rx.send_event(Gst.Event.new_eos())
    print("receiver EOS injected", flush=True)
    rx_rc = wait_eos(rx.get_bus(), 10 * Gst.SECOND)
    print("receiver", rx_rc, flush=True)

    tx.set_state(Gst.State.NULL)
    rx.set_state(Gst.State.NULL)

    size = os.path.getsize(args.out) if os.path.exists(args.out) else 0
    frames = size // 86400
    print(f"bytes={size} frames={frames}", flush=True)
    return 0 if rx_rc == "eos" else 1


if __name__ == "__main__":
    sys.exit(main())
