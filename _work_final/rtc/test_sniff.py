# -*- coding: utf-8 -*-
import time, collections
import l2sock

sock = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN)
et = collections.Counter()
first = {}
t0 = time.time()
while time.time() - t0 < 12:
    r = sock.recv(0.05)
    if r is None:
        continue
    raw = r[1]
    if len(raw) < 14:
        continue
    e = raw[12:14].hex()
    et[e] += 1
    if e not in first:
        first[e] = raw[:40].hex()
print("ethertype histogram over 12s:")
for e, c in et.most_common(10):
    print("  0x%s : %d" % (e, c))
print("first frame per type:")
for e, h in first.items():
    print("  0x%s : %s" % (e, h))
sock.close()
