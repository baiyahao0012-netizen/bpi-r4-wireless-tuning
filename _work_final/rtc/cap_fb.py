# -*- coding: utf-8 -*-
"""Count feedback frames (EtherType 0x88B6) arriving on one NIC."""
import sys, time
import l2sock, rtc2

dev = sys.argv[1] if len(sys.argv) > 1 else "MediaTek"
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0

s = l2sock.L2Socket(dev_substr=dev, direction=l2sock.PCAP_D_IN)
print("capturing on", s.desc, "for", secs, "s", flush=True)
t_end = time.perf_counter() + secs
n = 0
first = None
while time.perf_counter() < t_end:
    r = s.recv(0.2)
    if not r:
        continue
    raw = r[1]
    if len(raw) >= 14 and rtc2.ethertype_of(raw) == rtc2.ETH_FEEDBACK:
        n += 1
        if first is None:
            first = raw[:14].hex()
print("feedback frames seen: %d" % n)
if first:
    print("first frame header:", first)
s.close()
