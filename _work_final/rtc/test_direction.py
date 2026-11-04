# -*- coding: utf-8 -*-
"""Classify Wi-Fi frames as inbound (dst=our MAC) vs outbound (src=our MAC)."""
import time, collections
import l2sock

OURS = l2sock.mac_to_bytes("C0-35-32-19-CC-FB")
sock = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN)
inb = out = other = 0
in_et = collections.Counter()
out_et = collections.Counter()
t0 = time.time()
while time.time() - t0 < 10:
    r = sock.recv(0.05)
    if r is None:
        continue
    raw = r[1]
    if len(raw) < 14:
        continue
    dst, src = raw[0:6], raw[6:12]
    et = raw[12:14].hex()
    if dst == OURS:
        inb += 1; in_et[et] += 1
    elif src == OURS:
        out += 1; out_et[et] += 1
    else:
        other += 1
print("10s capture on 8852 (direction=PCAP_D_IN)")
print("  inbound  (dst=our MAC): %d   %s" % (inb, dict(in_et.most_common(5))))
print("  outbound (src=our MAC): %d   %s" % (out, dict(out_et.most_common(5))))
print("  neither               : %d" % other)
sock.close()
