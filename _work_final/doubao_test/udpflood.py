# -*- coding: utf-8 -*-
"""Paced multi-flow UDP background traffic.
usage: python udpflood.py <dst> <base_dport> <seconds> [src_ip] [n_flows] [mbit]
"""
import socket, sys, time

dst = sys.argv[1]; base = int(sys.argv[2]); dur = float(sys.argv[3])
src = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
n = int(sys.argv[5]) if len(sys.argv) > 5 else 1
rate_mbps = float(sys.argv[6]) if len(sys.argv) > 6 else 8.0
if n < 1 or rate_mbps <= 0:
    raise SystemExit("n_flows and mbit must be positive")

payload = b"x" * 1400
packet_bits = len(payload) * 8
interval = packet_bits / (rate_mbps * 1_000_000)
sockets = []
for _ in range(n):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if src:
        s.bind((src, 0))
    sockets.append(s)

t0 = time.monotonic()
deadline = t0 + dur
sent = 0
next_send = t0
try:
    while next_send < deadline:
        now = time.monotonic()
        if now < next_send:
            time.sleep(next_send - now)
        try:
            sockets[sent % n].sendto(payload, (dst, base + (sent % n)))
            sent += 1
        except OSError:
            pass
        next_send += interval
finally:
    for s in sockets:
        s.close()

elapsed = time.monotonic() - t0
actual = sent * packet_bits / max(elapsed, 0.1) / 1_000_000
print("flows=%d target=%.1f Mbit/s el=%.1fs pkts=%d actual=%.2f Mbit/s" %
      (n, rate_mbps, elapsed, sent, actual))
