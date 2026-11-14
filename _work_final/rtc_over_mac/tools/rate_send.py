#!/usr/bin/env python3
"""Rate-paced probe sender: UDP or raw L2 (0x88B5) frames.

Payload layout: MAGIC(4) | seq(u32) | ts_ns(u64) | flow(u32) | padding
L2 mode prepends the 12-byte RTC shim header used by l2_rtp_send.py.
"""
import argparse
import binascii
import socket
import struct
import sys
import time

MAGIC = b"PRB1"
HDR = struct.Struct("!4sIQI")
SHIM = struct.Struct("!BBHHBBHH")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["udp", "l2"], required=True)
    ap.add_argument("--dst", required=True, help="UDP: ip; L2: dst MAC aa:bb:..")
    ap.add_argument("--port", type=int, default=5100)
    ap.add_argument("--bind", default="")
    ap.add_argument("--iface", default="wlan1")
    ap.add_argument("--src", default="90:de:80:1c:6a:7a")
    ap.add_argument("--mbps", type=float, required=True)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--size", type=int, default=1400, help="payload bytes incl. probe header")
    ap.add_argument("--flow", type=int, default=1)
    a = ap.parse_args()

    hdr_len = HDR.size
    pad = b"\x00" * max(0, a.size - hdr_len)
    pps = a.mbps * 1e6 / 8.0 / a.size
    interval = 1.0 / pps if pps > 0 else 0

    if a.mode == "udp":
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
        if a.bind:
            s.bind((a.bind, 0))
        target = (a.dst, a.port)
        send = lambda b: s.sendto(b, target)
    else:
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x88B5))
        s.bind((a.iface, 0))
        dst_mac = bytes.fromhex(a.dst.replace(":", ""))
        src_mac = bytes.fromhex(a.src.replace(":", ""))
        eth = dst_mac + src_mac + b"\x88\xb5"

        def send(body):
            shim = SHIM.pack(0x11, 0, a.flow, len(body), 8, 12, 0, 0)
            crc = binascii.crc_hqx(shim + body, 0)
            shim = SHIM.pack(0x11, 0, a.flow, len(body), 8, 12, crc, 0)
            s.send(eth + shim + body)

    t0 = time.monotonic()
    end = t0 + a.seconds
    next_t = t0
    sent = 0
    t_first = None
    while True:
        now = time.monotonic()
        if now >= end:
            break
        if now < next_t:
            time.sleep(min(next_t - now, 0.002))
            continue
        body = HDR.pack(MAGIC, sent & 0xFFFFFFFF, time.monotonic_ns(), a.flow) + pad
        try:
            send(body)
        except OSError as e:
            print("send error after %d: %s" % (sent, e), file=sys.stderr)
            break
        if t_first is None:
            t_first = time.monotonic()
        sent += 1
        next_t += interval
        if next_t < now - 0.05:
            next_t = now
    el = time.monotonic() - t0
    tx_el = (time.monotonic() - t_first) if t_first else el
    print(
        "mode=%s sent=%d seconds=%.2f tx_seconds=%.2f pps=%.0f mbps=%.2f target_pps=%.0f target_mbps=%.2f size=%d"
        % (a.mode, sent, el, tx_el, sent / max(el, 1e-9), sent * a.size * 8 / max(el, 1e-9) / 1e6,
           pps, a.mbps, a.size),
        flush=True,
    )


if __name__ == "__main__":
    main()
