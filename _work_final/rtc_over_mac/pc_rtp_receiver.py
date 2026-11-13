#!/usr/bin/env python3
"""Windows-side RTP receiver used as an L1 reference probe.

Listens on the wired Ethernet address, parses RTP, rebuilds H.264 Annex-B,
and reports packet-level metrics plus decoded frame count.
This is a probe, not the final GStreamer receiver.
"""
import argparse
import json
import socket
import struct
import time

import av


def rtp_payload(raw):
    if len(raw) < 12:
        return None
    b0, b1 = raw[0], raw[1]
    if b0 >> 6 != 2:
        return None
    cc = b0 & 0x0F
    ext = (b0 >> 4) & 1
    pad = (b0 >> 5) & 1
    off = 12 + 4 * cc
    if ext:
        if len(raw) < off + 4:
            return None
        ext_len = struct.unpack("!H", raw[off + 2:off + 4])[0]
        off += 4 + 4 * ext_len
    end = len(raw) - (raw[-1] if pad and raw else 0)
    if off > end:
        return None
    return raw[off:end], b1 & 0x7F, struct.unpack("!H", raw[2:4])[0], struct.unpack("!I", raw[4:8])[0], struct.unpack("!I", raw[8:12])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="192.168.240.2")
    ap.add_argument("--port", type=int, default=5004)
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--out", default=r"D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\pc_rx.h264")
    args = ap.parse_args()

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 << 20)
    s.bind((args.host, args.port))
    s.settimeout(1.0)
    print(json.dumps({"event": "listening", "host": args.host, "port": args.port}), flush=True)

    out = bytearray()
    n = 0
    payload_bytes = 0
    seqs = []
    ssrcs = {}
    pts = set()
    first = last = None
    prev_transit = None
    jitter = 0.0
    fu = None
    end = time.time() + args.seconds
    while time.time() < end:
        try:
            data, _ = s.recvfrom(65535)
        except socket.timeout:
            continue
        r = rtp_payload(data)
        if not r:
            continue
        payload, pt, seq, ts, ssrc = r
        n += 1
        payload_bytes += len(payload)
        seqs.append(seq)
        ssrcs[ssrc] = ssrcs.get(ssrc, 0) + 1
        pts.add(ts)
        arrival = time.time()
        transit = arrival - ts / 90000.0
        if prev_transit is not None:
            d = abs(transit - prev_transit) * 1000.0
            jitter += (d - jitter) / 16.0
        prev_transit = transit
        first = first or (seq, ts, ssrc, pt, len(data))
        last = (seq, ts, ssrc, pt, len(data))

        if not payload:
            continue
        nal = payload[0] & 0x1F
        if 1 <= nal <= 23:
            out += b"\x00\x00\x00\x01" + payload
        elif nal == 24:
            i = 1
            while i + 2 <= len(payload):
                sz = struct.unpack("!H", payload[i:i + 2])[0]
                i += 2
                if sz <= 0 or i + sz > len(payload):
                    break
                out += b"\x00\x00\x00\x01" + payload[i:i + sz]
                i += sz
        elif nal == 28:
            if len(payload) < 2:
                continue
            fu_ind, fu_hdr = payload[0], payload[1]
            start = (fu_hdr >> 7) & 1
            finish = (fu_hdr >> 6) & 1
            typ = fu_hdr & 0x1F
            if start:
                fu = bytearray([(fu_ind & 0xE0) | typ])
            if fu is not None:
                fu += payload[2:]
                if finish:
                    out += b"\x00\x00\x00\x01" + bytes(fu)
                    fu = None
    s.close()
    open(args.out, "wb").write(out)

    gaps = sum(1 for a, b in zip(seqs, seqs[1:]) if ((b - a) & 0xFFFF) not in (0, 1))
    dup = len(seqs) - len(set(seqs))
    frames = 0
    decode_error = None
    try:
        ctx = av.CodecContext.create("h264", "r")
        with open(args.out, "rb") as fh:
            while True:
                chunk = fh.read(1 << 20)
                if not chunk:
                    break
                for packet in ctx.parse(chunk):
                    for _ in ctx.decode(packet):
                        frames += 1
        for _ in ctx.decode(None):
            frames += 1
    except Exception as e:
        decode_error = repr(e)

    print(json.dumps({
        "packets": n,
        "payload_bytes": payload_bytes,
        "seq_gaps": gaps,
        "duplicates": dup,
        "ssrcs": ssrcs,
        "unique_timestamps": len(pts),
        "jitter_ms": round(jitter, 3),
        "first": first,
        "last": last,
        "h264_bytes": len(out),
        "decoded_frames": frames,
        "decode_error": decode_error,
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
