# -*- coding: utf-8 -*-
"""Use the exact FbRx path the sender uses, count decoded reports."""
import sys, time
import txport, rtc2

iface = sys.argv[1] if len(sys.argv) > 1 else "MediaTek"
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 13.0

fb = txport.FbRx('l2', iface=iface)
print("FbRx on", fb.desc, flush=True)
t_end = time.perf_counter() + secs
got = 0
err = 0
while time.perf_counter() < t_end:
    try:
        p = fb.recv(0.2)
    except Exception as e:
        err += 1
        if err <= 3:
            print("recv error:", repr(e), flush=True)
        continue
    if p is None:
        continue
    try:
        d = rtc2.unpack_feedback(p)
        got += 1
        if got == 1:
            print("first report:", d, flush=True)
    except Exception as e:
        err += 1
        if err <= 3:
            print("parse error len=%d: %r" % (len(p), e), flush=True)
print("reports decoded: %d, errors: %d" % (got, err))
fb.close()
