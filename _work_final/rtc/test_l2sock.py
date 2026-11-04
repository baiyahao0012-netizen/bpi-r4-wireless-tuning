# -*- coding: utf-8 -*-
import l2sock, rtc2, time
devs = l2sock.list_devices()
print("interfaces:")
for n, d in devs:
    if any(k in d for k in ("GbE", "8852", "MediaTek")):
        print("  ", d)
eth = l2sock.L2Socket(dev_substr="GbE Family")
wifi = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN)
print("opened:", eth.desc, "|", wifi.desc)
wire = l2sock.mac_to_bytes("C0-35-32-19-CC-FB") + l2sock.mac_to_bytes("40-C2-BA-52-70-95") \
       + b"\x88\xb5" + rtc2.pack_header(0,0,0,1,0,1,4,1,0,0) + b"ping"
for _ in range(3):
    eth.send(wire); time.sleep(0.01)
got = 0
t0 = time.time()
while time.time() - t0 < 1.0:
    r = wifi.recv(0.1)
    if r and len(r[1]) >= 14 and r[1][12:14] == b"\x88\xb5":
        got += 1
print("tx=%d rx=%d -> %s" % (eth.tx, got, "PASS" if got == 3 else "FAIL"))
eth.close(); wifi.close()
