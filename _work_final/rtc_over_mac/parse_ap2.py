# -*- coding: utf-8 -*-
"""Parse the AP-side RTP pcap, rebuild H.264 Annex-B, and decode it."""
import struct
import sys
from collections import Counter

from scapy.all import PcapReader, UDP

PCAP = r"D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\ap2.pcap"
OUT = r"D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\ap2_rx.h264"


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
    out = bytearray()
    n = 0
    seqs = []
    ssrcs = Counter()
    pts = Counter()
    fu = None
    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if UDP not in pkt:
                continue
            u = pkt[UDP]
            if u.dport != 5004:
                continue
            r = rtp_payload(bytes(u.payload))
            if not r:
                continue
            payload, pt, seq, ts, ssrc = r
            n += 1
            seqs.append(seq)
            ssrcs[ssrc] += 1
            pts[ts] += 1
            if not payload:
                continue
            nal = payload[0] & 0x1F
            if 1 <= nal <= 23:
                out += b"\x00\x00\x00\x01" + payload
            elif nal == 24:  # STAP-A
                i = 1
                while i + 2 <= len(payload):
                    sz = struct.unpack("!H", payload[i:i + 2])[0]
                    i += 2
                    if sz <= 0 or i + sz > len(payload):
                        break
                    out += b"\x00\x00\x00\x01" + payload[i:i + sz]
                    i += sz
            elif nal == 28:  # FU-A
                if len(payload) < 2:
                    continue
                fu_ind = payload[0]
                fu_hdr = payload[1]
                start = (fu_hdr >> 7) & 1
                end = (fu_hdr >> 6) & 1
                typ = fu_hdr & 0x1F
                if start:
                    fu = bytearray([(fu_ind & 0xE0) | typ])
                if fu is not None:
                    fu += payload[2:]
                    if end:
                        out += b"\x00\x00\x00\x01" + bytes(fu)
                        fu = None
    open(OUT, "wb").write(out)
    gaps = sum(1 for a, b in zip(seqs, seqs[1:]) if ((b - a) & 0xFFFF) not in (0, 1))
    print("packets", n)
    print("seq_first", seqs[0] if seqs else None, "seq_last", seqs[-1] if seqs else None)
    print("seq_gaps", gaps)
    print("ssrc", ssrcs.most_common(3))
    print("unique_timestamps", len(pts))
    print("h264_bytes", len(out), "->", OUT)

    try:
        import av
        ctx = av.CodecContext.create("h264", "r")
        frames = 0
        with av.open(OUT) as container:
            for frame in container.decode(video=0):
                frames += 1
        print("decoded_frames", frames)
    except Exception as e:
        print("decode_error", repr(e))


if __name__ == "__main__":
    main()
