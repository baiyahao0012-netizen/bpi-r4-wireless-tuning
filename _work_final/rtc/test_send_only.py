# -*- coding: utf-8 -*-
"""Send-only: identical loop to test_control but no receive. For A/B testing."""
import time, sys
import rtc2, l2sock

n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.005
dst = l2sock.mac_to_bytes("C0-35-32-19-CC-FB")
src = l2sock.mac_to_bytes("40-C2-BA-52-70-95")
eth = l2sock.L2Socket(dev_substr="GbE Family")
t_next = time.perf_counter()
for i in range(n):
    fr, _ = rtc2.chunk_frame(b"P" * 1200, frame_id=i, pts=0, send_ts_us=0, seq_start=i)
    eth.send(dst + src + b"\x88\xb5" + fr[0])
    t_next += interval
    d = t_next - time.perf_counter()
    if d > 0:
        time.sleep(d)
    else:
        t_next = time.perf_counter()
print("sent %d frames" % n)
eth.close()
