import time, rtc2, l2sock
WIFI_STA = 'C0-35-32-19-CC-FB'
ETH      = '40-C2-BA-52-70-95'
dst = l2sock.mac_to_bytes(WIFI_STA)
src = l2sock.mac_to_bytes(ETH)
out = l2sock.L2Socket(dev_substr='GbE Family', direction=l2sock.PCAP_D_OUT)
inn = l2sock.L2Socket(dev_substr='8852', direction=l2sock.PCAP_D_IN)
print("tx=%s rx=%s" % (out.desc, inn.desc))
for i in range(5):
    fb = rtc2.pack_feedback(i, 50000, 4000, 60000, 0, 1500, 10, 0, 40)
    out.send(dst + src + b'\x88\xb6' + fb)
    time.sleep(0.05)
got = []
t0 = time.perf_counter()
while time.perf_counter() - t0 < 2.0:
    r = inn.recv(0.1)
    if r is None:
        continue
    ts, raw = r
    if len(raw) >= 14 and raw[12:14] == b'\x88\xb6':
        try:
            f = rtc2.unpack_feedback(raw[14:14 + rtc2.FB_LEN])
            got.append(f['fb_seq'])
        except Exception as e:
            got.append('bad:%r' % e)
print("feedback seen on Wi-Fi: %d  seq=%s" % (len(got), got))
out.close(); inn.close()
