#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 video/QA protocol shared by the Pi sender and the laptop receiver.

Frame layout (Ethernet II, reused EtherTypes):
  0x88B5  video fragment
  0x88B6  question (magic Q01) / answer stream (magic A01)

Video fragment body:
  VI: frame_idx u32 | pts_us u64 | frag_idx u16 | frag_total u16 | plen u16 | payload
  18-byte header, max 1500-byte frame (MTU 1500, 2296 fails with EMSGSIZE).
"""
import struct

ETH_VIDEO = 0x88B5
ETH_QA = 0x88B6
MAGIC_Q = b"Q01"
MAGIC_A = b"A01"

VI = struct.Struct("!IQHHH")   # frame_idx, pts_us, frag_idx, frag_total, plen
QH = struct.Struct("!IIQQH")   # qid, frame_idx, pts_us, t0_ns, tlen
AH = struct.Struct("!IIBQH")   # qid, seq, flags, t2_ns, tlen

ETH_HDR = 14
FRAME_MAX = 1500
VID_PAYLOAD = FRAME_MAX - ETH_HDR - VI.size      # 1468


def mac(s):
    return bytes.fromhex(s.replace(":", "").replace("-", ""))


def video_frag(dst, src, frame_idx, pts_us, frag_idx, frag_total, payload):
    body = VI.pack(frame_idx, pts_us, frag_idx, frag_total, len(payload)) + payload
    return dst + src + struct.pack("!H", ETH_VIDEO) + body


def question(dst, src, qid, frame_idx, pts_us, t0_ns, text):
    tb = text.encode("utf-8")
    body = MAGIC_Q + QH.pack(qid, frame_idx, pts_us, t0_ns, len(tb)) + tb
    return dst + src + struct.pack("!H", ETH_QA) + body


def answer(dst, src, qid, seq, flags, t2_ns, text):
    tb = text.encode("utf-8")
    body = MAGIC_A + AH.pack(qid, seq, flags, t2_ns, len(tb)) + tb
    return dst + src + struct.pack("!H", ETH_QA) + body


def parse(raw):
    """Return dict for QA frames or video fragments; None if not ours."""
    if len(raw) < ETH_HDR + 2:
        return None
    et = struct.unpack("!H", raw[12:14])[0]
    body = raw[ETH_HDR:]
    if et == ETH_VIDEO:
        if len(body) < VI.size:
            return None
        idx, pts, fi, ft, plen = VI.unpack(body[:VI.size])
        return {"type": "video", "frame_idx": idx, "pts_us": pts,
                "frag_idx": fi, "frag_total": ft,
                "payload": body[VI.size:VI.size + plen]}
    if et == ETH_QA:
        if body[:3] == MAGIC_Q and len(body) >= 3 + QH.size:
            qid, idx, pts, t0, tlen = QH.unpack(body[3:3 + QH.size])
            txt = body[3 + QH.size:3 + QH.size + tlen]
            return {"type": "question", "qid": qid, "frame_idx": idx,
                    "pts_us": pts, "t0_ns": t0, "text": txt.decode("utf-8", "replace")}
        if body[:3] == MAGIC_A and len(body) >= 3 + AH.size:
            qid, seq, flags, t2, tlen = AH.unpack(body[3:3 + AH.size])
            txt = body[3 + AH.size:3 + AH.size + tlen]
            return {"type": "answer", "qid": qid, "seq": seq, "flags": flags,
                    "t2_ns": t2, "text": txt.decode("utf-8", "replace")}
    return None
