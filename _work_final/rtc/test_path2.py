# -*- coding: utf-8 -*-
import time, rtc2, l2sock

eth = l2sock.L2Socket(dev_substr="GbE Family")
wifi = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN)
DST = l2sock.mac_to_bytes("C0-35-32-19-CC-FB")
SRC = l2sock.mac_to_bytes("40-C2-BA-52-70-95")

def send_n(payload, n, tag):
    for i in range(n):
        fr, _ = rtc2.chunk_frame(payload, frame_id=i, pts=0, send_ts_us=0, seq_start=i)
        eth.send(DST + SRC + b"\x88\xb5" + fr[0])
        time.sleep(0.005)
    print("sent %d x %s (payload %d)" % (n, tag, len(payload)))

send_n(b"small", 20, "small")
send_n(b"L" * 1200, 20, "large")
send_n(b"M" * 600, 20, "medium")

small = large = med = 0
t0 = time.time()
while time.time() - t0 < 2.0:
    r = wifi.recv(0.05)
    if r is None:
        continue
    raw = r[1]
    if len(raw) >= 14 and raw[12:14] == b"\x88\xb5":
        try:
            h, body = rtc2.payload_of(raw)
        except rtc2.Rtc2Error:
            continue
        if body.startswith(b"small"): small += 1
        elif body.startswith(b"L"): large += 1
        elif body.startswith(b"M"): med += 1
print("received: small=%d/20  medium=%d/20  large=%d/20" % (small, med, large))
eth.close(); wifi.close()
