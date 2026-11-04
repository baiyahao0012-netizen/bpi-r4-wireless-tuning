# -*- coding: utf-8 -*-
import struct, sys, traceback
import rtc2

PASS = FAIL = 0
def check(name, fn):
    global PASS, FAIL
    try:
        fn(); PASS += 1; print("[PASS]", name)
    except Exception as e:
        FAIL += 1; print("[FAIL]", name, "->", repr(e))

def eq(a, b, msg=""):
    if a != b:
        raise AssertionError("%s expected %r got %r" % (msg, b, a))

# --- sizes ---
check("header size 28", lambda: eq(rtc2.HDR_LEN, 28))
check("feedback size 40", lambda: eq(rtc2.FB_LEN, 40))

# --- header roundtrip normal ---
def t_roundtrip():
    p = rtc2.pack_header(rtc2.T_VIDEO, rtc2.F_KEYFRAME | rtc2.F_FRAME_START,
                         rtc2.S_VIDEO, 1234, 2, 5, 1200, 777, 90000, 123456789)
    eq(len(p), 28)
    h = rtc2.unpack_header(p)
    eq(h["type"], 0); eq(h["flags"], 0b0110); eq(h["stream_id"], 0)
    eq(h["seq"], 1234); eq(h["chunk_idx"], 2); eq(h["chunk_cnt"], 5)
    eq(h["payload_len"], 1200); eq(h["frame_id"], 777)
    eq(h["pts"], 90000); eq(h["send_ts_us"], 123456789)
check("header roundtrip", t_roundtrip)

# --- header boundary values ---
def t_boundary():
    p = rtc2.pack_header(255, 255, 255, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF,
                         0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, rsv=255)
    h = rtc2.unpack_header(p)
    eq(h["seq"], 0xFFFF); eq(h["frame_id"], 0xFFFFFFFF); eq(h["rsv"], 255)
    p0 = rtc2.pack_header(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    h0 = rtc2.unpack_header(p0)
    eq(h0["pts"], 0); eq(h0["payload_len"], 0)
check("header boundary min/max", t_boundary)

# --- errors ---
def t_bad_magic():
    p = bytearray(rtc2.pack_header(0,0,0,1,0,1,0,0,0,0)); p[0] = 0xFF
    try:
        rtc2.unpack_header(bytes(p)); raise AssertionError("should have raised")
    except rtc2.Rtc2Error: pass
check("bad magic rejected", t_bad_magic)

def t_short():
    try:
        rtc2.unpack_header(b"\x00" * 27); raise AssertionError("should have raised")
    except rtc2.Rtc2Error: pass
check("short header rejected", t_short)

def t_range():
    for kw in ({"seq": 70000}, {"chunk_idx": -1}, {"payload_len": 65536},
               {"frame_id": 2**32}, {"pts": -5}):
        args = dict(type_=0, flags=0, stream_id=0, seq=1, chunk_idx=0, chunk_cnt=1,
                    payload_len=0, frame_id=0, pts=0, send_ts_us=0)
        args.update(kw)
        try:
            rtc2.pack_header(**args); raise AssertionError("should have raised for %r" % kw)
        except rtc2.Rtc2Error: pass
check("range validation", t_range)

# --- chunking ---
def t_chunks_exact():
    payload = bytes(range(256)) * 10   # 2560 = 1200 + 1200 + 160
    fr, nxt = rtc2.chunk_frame(payload, frame_id=5, pts=100, send_ts_us=200,
                               seq_start=0, keyframe=True)
    eq(len(fr), 3, "chunk count")
    eq(nxt, 3, "next seq")
    hs = [rtc2.unpack_header(f) for f in fr]
    eq([h["chunk_idx"] for h in hs], [0, 1, 2])
    eq([h["chunk_cnt"] for h in hs], [3, 3, 3])
    eq([h["payload_len"] for h in hs], [1200, 1200, 160])
    eq([h["seq"] for h in hs], [0, 1, 2])
    for i, h in enumerate(hs):
        eq(bool(h["flags"] & rtc2.F_FRAME_START), i == 0, "start flag %d" % i)
        eq(bool(h["flags"] & rtc2.F_FRAME_END), i == 2, "end flag %d" % i)
        eq(bool(h["flags"] & rtc2.F_KEYFRAME), True, "keyframe flag %d" % i)
    rebuilt = b"".join(f[rtc2.HDR_LEN:] for f in fr)
    eq(rebuilt, payload, "reassembled payload")
    eq(len(rebuilt), sum(h["payload_len"] for h in hs), "sum of payload_len")
check("chunking + flags + reassembly", t_chunks_exact)

def t_chunks_single():
    fr, nxt = rtc2.chunk_frame(b"x" * 100, 1, 0, 0, 0)
    eq(len(fr), 1)
    h = rtc2.unpack_header(fr[0])
    eq(h["flags"] & rtc2.F_FRAME_START, rtc2.F_FRAME_START)
    eq(h["flags"] & rtc2.F_FRAME_END, rtc2.F_FRAME_END)
    eq(h["flags"] & rtc2.F_KEYFRAME, 0)
check("single chunk has both start+end", t_chunks_single)

def t_chunks_empty():
    fr, nxt = rtc2.chunk_frame(b"", 1, 0, 0, 7)
    eq(len(fr), 0); eq(nxt, 7)
check("empty payload -> no chunks", t_chunks_empty)

def t_seq_wrap():
    fr, nxt = rtc2.chunk_frame(b"y" * 3600, 1, 0, 0, 0xFFFE)
    eq(len(fr), 3)
    eq(nxt, 0x10001)
    eq([rtc2.unpack_header(f)["seq"] for f in fr], [0xFFFE, 0xFFFF, 0])
check("seq wraps at 16 bits", t_seq_wrap)

def t_audio_stream():
    fr, _ = rtc2.chunk_frame(b"a" * 50, 3, 0, 0, 0, stream_id=rtc2.S_AUDIO)
    h = rtc2.unpack_header(fr[0])
    eq(h["type"], rtc2.T_AUDIO); eq(h["stream_id"], rtc2.S_AUDIO)
check("audio stream sets type", t_audio_stream)

def t_bad_chunk_size():
    try:
        rtc2.chunk_frame(b"z", 1, 0, 0, 0, chunk_size=2000)
        raise AssertionError("should have raised")
    except rtc2.Rtc2Error: pass
check("chunk_size over MAX rejected", t_bad_chunk_size)

# --- feedback ---
def t_fb():
    p = rtc2.pack_feedback(9, 50000, 123456, 4200, 15, 800, 100, 3, 555)
    eq(len(p), 40)
    f = rtc2.unpack_feedback(p)
    eq(f["fb_seq"], 9); eq(f["window_us"], 50000); eq(f["recv_bytes"], 123456)
    eq(f["q_us"], 4200); eq(f["loss_permille"], 15); eq(f["jitter_us"], 800)
    eq(f["frames_ok"], 100); eq(f["frames_lost"], 3); eq(f["max_frame_id"], 555)
check("feedback roundtrip", t_fb)

def t_fb_bad():
    p = bytearray(rtc2.pack_feedback(1,1,1,1,0,0,0,0,0)); p[0] ^= 0xFF
    try:
        rtc2.unpack_feedback(bytes(p)); raise AssertionError("should raise")
    except rtc2.Rtc2Error: pass
    try:
        rtc2.unpack_feedback(b"\x00"*10); raise AssertionError("should raise")
    except rtc2.Rtc2Error: pass
check("feedback errors", t_fb_bad)

# --- ethernet framing ---
def t_eth():
    payload = b"hello world" * 10
    fr, _ = rtc2.chunk_frame(payload, 2, 5, 6, 0)
    eth = b"\xaa"*6 + b"\xbb"*6 + b"\x88\xb5" + fr[0]
    eq(rtc2.ethertype_of(eth), rtc2.ETH_DATA)
    h, body = rtc2.payload_of(eth)
    eq(h["frame_id"], 2); eq(body, payload)
check("ethernet frame parse", t_eth)

def t_eth_truncated():
    fr, _ = rtc2.chunk_frame(b"q"*100, 2, 5, 6, 0)
    eth = b"\xaa"*6 + b"\xbb"*6 + b"\x88\xb5" + fr[0][:40]
    try:
        rtc2.payload_of(eth); raise AssertionError("should raise")
    except rtc2.Rtc2Error: pass
check("truncated payload rejected", t_eth_truncated)

print()
print("SUMMARY: %d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
