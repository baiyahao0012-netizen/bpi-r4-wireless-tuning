# -*- coding: utf-8 -*-
"""Background UDP load towards the receiver, to contend for airtime."""
import socket, sys, time
dst, secs, mbps = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
payload = b'x' * 1400
t0 = time.perf_counter()
sent = 0
target_pps = mbps * 1e6 / 8 / 1400
next_t = t0
while time.perf_counter() - t0 < secs:
    s.sendto(payload, (dst, 9999))
    sent += 1
    next_t += 1.0 / target_pps
    d = next_t - time.perf_counter()
    if d > 0:
        time.sleep(d)
el = time.perf_counter() - t0
print("blaster: %d pkts in %.1fs = %.1f Mbps" % (sent, el, sent * 1400 * 8 / el / 1e6))
