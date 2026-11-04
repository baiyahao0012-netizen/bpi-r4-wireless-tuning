# -*- coding: utf-8 -*-
"""Control: sustained raw frames Ethernet -> each Wi-Fi STA, interleaved drain."""
import time, rtc2, l2sock

eth = l2sock.L2Socket(dev_substr="GbE Family")
SRC = l2sock.mac_to_bytes("40-C2-BA-52-70-95")
TARGETS = [("MediaTek", "90-DE-80-1C-6A-7A"), ("8852", "C0-35-32-19-CC-FB")]

def run(sub, macstr, n=300, interval=0.005):
    rx = l2sock.L2Socket(dev_substr=sub, direction=l2sock.PCAP_D_IN)
    dst = l2sock.mac_to_bytes(macstr)
    got = 0
    seqs = set()
    t_next = time.perf_counter()
    for i in range(n):
        fr, _ = rtc2.chunk_frame(b"P" * 1200, frame_id=i, pts=0, send_ts_us=0, seq_start=i)
        try:
            eth.send(dst + SRC + b"\x88\xb5" + fr[0])
        except Exception as e:
            print("  send err", e); break
        # drain whatever arrived
        while True:
            r = rx.recv(0.0)
            if r is None: break
            raw = r[1]
            if len(raw) >= 14 and raw[12:14] == b"\x88\xb5":
                try:
                    h = rtc2.unpack_header(raw[14:])
                except rtc2.Rtc2Error:
                    continue
                seqs.add(h["frame_id"]); got += 1
        t_next += interval
        d = t_next - time.perf_counter()
        if d > 0: time.sleep(d)
        else: t_next = time.perf_counter()
    # final drain
    t0 = time.time()
    while time.time() - t0 < 1.5:
        r = rx.recv(0.02)
        if r is None: continue
        raw = r[1]
        if len(raw) >= 14 and raw[12:14] == b"\x88\xb5":
            try:
                h = rtc2.unpack_header(raw[14:])
            except rtc2.Rtc2Error:
                continue
            seqs.add(h["frame_id"]); got += 1
    rx.close()
    print("  %-9s sent=%d received=%d unique=%d  loss=%.1f%%"
          % (sub, n, got, len(seqs), 100.0 * (n - len(seqs)) / n))

for sub, mac in TARGETS:
    run(sub, mac)
eth.close()
