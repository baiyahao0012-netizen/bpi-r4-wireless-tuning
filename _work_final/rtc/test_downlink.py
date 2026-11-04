# -*- coding: utf-8 -*-
"""Count inbound frames by source MAC during a board flood."""
import time, collections
import l2sock

OURS = l2sock.mac_to_bytes("C0-35-32-19-CC-FB")
sock = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN)
srcs = collections.Counter()
big = 0
t0 = time.time()
while time.time() - t0 < 14:
    r = sock.recv(0.05)
    if r is None:
        continue
    raw = r[1]
    if len(raw) < 14 or raw[0:6] != OURS:
        continue
    srcs[raw[6:12].hex()] += 1
    if len(raw) > 1200:
        big += 1
print("inbound frames by source MAC (14s):")
for m, c in srcs.most_common(6):
    print("   %s : %d" % (m, c))
print("inbound frames >1200 bytes: %d" % big)
sock.close()
