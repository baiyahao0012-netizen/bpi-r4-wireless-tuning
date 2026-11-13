#!/usr/bin/env python3
"""L2 shim receiver with a simple sequence reorder buffer, then PyAV decode."""
import argparse
import binascii
import struct
from collections import Counter

from scapy.all import Ether, sniff, conf

conf.bufsize = 64 * 1024 * 1024
conf.sniff_promisc = False
conf.use_pcap = True

IFACE = r"\Device\NPF_{A2958734-FBD5-4E72-AD1C-362588589CD1}"
ETHERTYPE = 0x88B5


def parse_rtp(raw):
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
        off += 4 + 4 * struct.unpack("!H", raw[off + 2:off + 4])[0]
    end = len(raw) - (raw[-1] if pad and raw else 0)
    if off > end:
        return None
    return raw[off:end], b1 & 0x7F, struct.unpack("!H", raw[2:4])[0], struct.unpack("!I", raw[4:8])[0], struct.unpack("!I", raw[8:12])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=100)
    ap.add_argument("--out", default=r"D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\l2_rx_reorder.h264")
    args = ap.parse_args()

    packets = {}
    order = []
    bad = 0
    dup = 0

    def cb(pkt):
        nonlocal bad, dup
        if Ether not in pkt or pkt[Ether].type != ETHERTYPE:
            return
        raw = bytes(pkt[Ether].payload)
        if len(raw) < 12:
            bad += 1
            return
        ver_type, flags, flow, plen, ttl, hlen, crc, stream = struct.unpack("!BBHHBBHH", raw[:12])
        if (ver_type >> 4) != 1 or hlen != 12 or len(raw) < hlen + plen:
            bad += 1
            return
        rtp = raw[hlen:hlen + plen]
        hdr0 = bytearray(raw[:12])
        hdr0[8:10] = b"\x00\x00"
        if binascii.crc_hqx(bytes(hdr0) + rtp, 0) != crc:
            bad += 1
            return
        r = parse_rtp(rtp)
        if not r:
            return
        _, _, seq, _, _ = r
        if seq in packets:
            dup += 1
            return
        packets[seq] = rtp
        order.append(seq)

    sniff(iface=IFACE, filter="ether proto 0x88b5", timeout=args.seconds, store=False, prn=cb)

    base = order[0] if order else 0
    ordered = [packets[k] for k in sorted(packets, key=lambda s: (s - base) & 0xFFFF)]
    out = bytearray()
    seqs = []
    ssrcs = Counter()
    timestamps = set()
    fu = None
    for rtp in ordered:
        r = parse_rtp(rtp)
        if not r:
            continue
        payload, pt, seq, ts, ssrc = r
        seqs.append(seq)
        ssrcs[ssrc] += 1
        timestamps.add(ts)
        if not payload:
            continue
        nal = payload[0] & 0x1F
        if 1 <= nal <= 23:
            out.extend(b"\x00\x00\x00\x01" + payload)
        elif nal == 24:
            i = 1
            while i + 2 <= len(payload):
                sz = struct.unpack("!H", payload[i:i + 2])[0]
                i += 2
                if sz <= 0 or i + sz > len(payload):
                    break
                out.extend(b"\x00\x00\x00\x01" + payload[i:i + sz])
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
                fu.extend(payload[2:])
                if finish:
                    out.extend(b"\x00\x00\x00\x01" + bytes(fu))
                    fu = None

    open(args.out, "wb").write(out)
    gaps = sum(1 for a, b in zip(seqs, seqs[1:]) if ((b - a) & 0xFFFF) not in (0, 1))
    frames = 0
    decode_error = None
    try:
        import av
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

    print("packets", len(ordered), "dup", dup, "bad", bad, "seq_gaps", gaps,
          "timestamps", len(timestamps), "ssrcs", dict(ssrcs),
          "h264_bytes", len(out), "frames", frames, "decode_error", decode_error, flush=True)


if __name__ == "__main__":
    main()
