# -*- coding: utf-8 -*-
"""RTC2 protocol layer: header pack/unpack, chunking, feedback frames.

Wire format (28 bytes, network byte order):
    magic       u32  0x52544332 'RTC2'
    type        u8   0=video 1=audio 2=feedback 3=control
    flags       u8   bit0 FEC parity, bit1 keyframe, bit2 frame_start,
                     bit3 frame_end, bit4 retransmit, bit5 probe
    stream_id   u8   0=video 1=audio
    rsv         u8
    seq         u16  global, wraps
    chunk_idx   u16
    chunk_cnt   u16
    payload_len u16
    frame_id    u32
    pts         u32  90 kHz
    send_ts_us  u32  microseconds (low 32 bits of monotonic clock)
"""
import struct

MAGIC = 0x52544332          # 'RTC2'
FB_MAGIC = 0x46424B31       # 'FBK1'

ETH_DATA = 0x88B5
ETH_FEEDBACK = 0x88B6
ETH_CONTROL = 0x88B7

T_VIDEO, T_AUDIO, T_FEEDBACK, T_CONTROL = 0, 1, 2, 3
S_VIDEO, S_AUDIO = 0, 1

F_PARITY      = 1 << 0
F_KEYFRAME    = 1 << 1
F_FRAME_START = 1 << 2
F_FRAME_END   = 1 << 3
F_RETRANSMIT  = 1 << 4
F_PROBE       = 1 << 5

HDR_LEN = 28
HDR_FMT = "!IBBBBHHHHIII"
FB_LEN = 40
FB_FMT = "!IIIIIHHIIIHH"

DEFAULT_CHUNK = 1200
MAX_CHUNK = 1472            # 1500 - 28 header, keep margin

assert struct.calcsize(HDR_FMT) == HDR_LEN, struct.calcsize(HDR_FMT)
assert struct.calcsize(FB_FMT) == FB_LEN, struct.calcsize(FB_FMT)


class Rtc2Error(ValueError):
    pass


def pack_header(type_, flags, stream_id, seq, chunk_idx, chunk_cnt,
                payload_len, frame_id, pts, send_ts_us, rsv=0, magic=MAGIC):
    if not 0 <= type_ <= 255 or not 0 <= flags <= 255:
        raise Rtc2Error("type/flags out of range")
    if not 0 <= stream_id <= 255 or not 0 <= rsv <= 255:
        raise Rtc2Error("stream_id/rsv out of range")
    for name, v in (("seq", seq), ("chunk_idx", chunk_idx), ("chunk_cnt", chunk_cnt),
                    ("payload_len", payload_len)):
        if not 0 <= v <= 0xFFFF:
            raise Rtc2Error("%s out of u16 range: %r" % (name, v))
    for name, v in (("frame_id", frame_id), ("pts", pts), ("send_ts_us", send_ts_us)):
        if not 0 <= v <= 0xFFFFFFFF:
            raise Rtc2Error("%s out of u32 range: %r" % (name, v))
    return struct.pack(HDR_FMT, magic, type_, flags, stream_id, rsv,
                       seq, chunk_idx, chunk_cnt, payload_len,
                       frame_id, pts, send_ts_us)


def unpack_header(buf):
    """Return dict or raise Rtc2Error. Accepts buffer with >= HDR_LEN bytes."""
    if len(buf) < HDR_LEN:
        raise Rtc2Error("short header: %d < %d" % (len(buf), HDR_LEN))
    (magic, type_, flags, stream_id, rsv, seq, chunk_idx, chunk_cnt,
     payload_len, frame_id, pts, send_ts_us) = struct.unpack(HDR_FMT, buf[:HDR_LEN])
    if magic != MAGIC:
        raise Rtc2Error("bad magic 0x%08x" % magic)
    return dict(magic=magic, type=type_, flags=flags, stream_id=stream_id, rsv=rsv,
                seq=seq, chunk_idx=chunk_idx, chunk_cnt=chunk_cnt,
                payload_len=payload_len, frame_id=frame_id, pts=pts,
                send_ts_us=send_ts_us)


def chunk_frame(payload, frame_id, pts, send_ts_us, seq_start,
                stream_id=S_VIDEO, keyframe=False, chunk_size=DEFAULT_CHUNK,
                type_=None):
    """Split payload into chunks. Returns (list_of_bytes, next_seq).

    Each element is a complete wire frame: 28-byte header + payload slice.
    """
    if chunk_size < 1 or chunk_size > MAX_CHUNK:
        raise Rtc2Error("chunk_size must be 1..%d" % MAX_CHUNK)
    if type_ is None:
        type_ = T_AUDIO if stream_id == S_AUDIO else T_VIDEO
    n = len(payload)
    cnt = (n + chunk_size - 1) // chunk_size if n else 0
    if cnt == 0:
        return [], seq_start
    out = []
    seq = seq_start
    for i in range(cnt):
        off = i * chunk_size
        piece = payload[off:off + chunk_size]
        flags = 0
        if i == 0:
            flags |= F_FRAME_START
        if i == cnt - 1:
            flags |= F_FRAME_END
        if keyframe:
            flags |= F_KEYFRAME
        out.append(pack_header(type_, flags, stream_id, seq & 0xFFFF,
                               i, cnt, len(piece), frame_id, pts, send_ts_us)
                   + bytes(piece))
        seq += 1
    return out, seq


def pack_feedback(fb_seq, window_us, recv_bytes, q_us, loss_permille,
                  jitter_us, frames_ok, frames_lost, max_frame_id, rsv=0, rsv2=0):
    for name, v in (("fb_seq", fb_seq), ("window_us", window_us),
                    ("recv_bytes", recv_bytes), ("q_us", q_us),
                    ("frames_ok", frames_ok), ("frames_lost", frames_lost),
                    ("max_frame_id", max_frame_id)):
        if not 0 <= v <= 0xFFFFFFFF:
            raise Rtc2Error("%s out of u32 range" % name)
    for name, v in (("loss_permille", loss_permille), ("jitter_us", jitter_us),
                    ("rsv", rsv), ("rsv2", rsv2)):
        if not 0 <= v <= 0xFFFF:
            raise Rtc2Error("%s out of u16 range" % name)
    return struct.pack(FB_FMT, FB_MAGIC, fb_seq, window_us, recv_bytes, q_us,
                       loss_permille, jitter_us, frames_ok, frames_lost,
                       max_frame_id, rsv, rsv2)


def unpack_feedback(buf):
    if len(buf) < FB_LEN:
        raise Rtc2Error("short feedback: %d" % len(buf))
    (magic, fb_seq, window_us, recv_bytes, q_us, loss_permille, jitter_us,
     frames_ok, frames_lost, max_frame_id, rsv, rsv2) = struct.unpack(FB_FMT, buf[:FB_LEN])
    if magic != FB_MAGIC:
        raise Rtc2Error("bad fb magic 0x%08x" % magic)
    return dict(fb_seq=fb_seq, window_us=window_us, recv_bytes=recv_bytes, q_us=q_us,
                loss_permille=loss_permille, jitter_us=jitter_us,
                frames_ok=frames_ok, frames_lost=frames_lost,
                max_frame_id=max_frame_id, rsv=rsv, rsv2=rsv2)


def ethertype_of(wire):
    """Read EtherType from a full ethernet frame."""
    if len(wire) < 14:
        raise Rtc2Error("short ethernet frame")
    return (wire[12] << 8) | wire[13]


def payload_of(wire):
    """Return RTC2 body (after 28-byte header) of a full ethernet frame."""
    h = unpack_header(wire[14:])
    body = wire[14 + HDR_LEN: 14 + HDR_LEN + h["payload_len"]]
    if len(body) != h["payload_len"]:
        raise Rtc2Error("truncated payload: %d != %d" % (len(body), h["payload_len"]))
    return h, body
