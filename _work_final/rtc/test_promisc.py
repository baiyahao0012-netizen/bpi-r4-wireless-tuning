# -*- coding: utf-8 -*-
import time, sys
import l2sock, rtc2

promisc = (len(sys.argv) < 2) or (sys.argv[1] != "0")
sock = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN, promisc=promisc)
print("listening promisc=%s" % promisc, flush=True)
n = 0; seqs = set()
t0 = time.time()
while time.time() - t0 < 13:
    r = sock.recv(0.05)
    if r is None:
        continue
    raw = r[1]
    if len(raw) >= 14 and raw[12:14] == b"\x88\xb5":
        try:
            h = rtc2.unpack_header(raw[14:])
        except rtc2.Rtc2Error:
            continue
        seqs.add(h["frame_id"]); n += 1
print("promisc=%s received=%d unique=%d" % (promisc, n, len(seqs)))
sock.close()
