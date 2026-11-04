import time, rtc2, l2sock
dst = l2sock.mac_to_bytes('C0-35-32-19-CC-FB')
src = l2sock.mac_to_bytes('40-C2-BA-52-70-95')
out = l2sock.L2Socket(dev_substr='GbE Family', direction=l2sock.PCAP_D_OUT)
inn = l2sock.L2Socket(dev_substr='8852', direction=l2sock.PCAP_D_IN)
ET = rtc2.ETH_FEEDBACK.to_bytes(2, 'big')

def trial(rate_hz, secs, copies):
    sent = 0
    t0 = time.perf_counter()
    tick = 0
    nxt = t0
    while time.perf_counter() - t0 < secs:
        fb = rtc2.pack_feedback(tick, 50000, 1000, 50000, 0, 1000, 1, 0, 1)
        for _ in range(copies):
            out.send(dst + src + ET + fb)
            sent += 1
        tick += 1
        nxt += 1.0 / rate_hz
        d = nxt - time.perf_counter()
        if d > 0:
            time.sleep(d)
    # drain
    got = 0
    seen = set()
    t1 = time.perf_counter()
    while time.perf_counter() - t1 < 0.8:
        r = inn.recv(0.05)
        if r is None:
            continue
        ts, raw = r
        if rtc2.ethertype_of(raw) == rtc2.ETH_FEEDBACK:
            got += 1
            try:
                seen.add(rtc2.unpack_feedback(raw[14:14+rtc2.FB_LEN])['fb_seq'])
            except Exception:
                pass
    print("rate=%3d Hz copies=%d sent=%4d received=%4d (%.0f%%) distinct=%3d/%3d"
          % (rate_hz, copies, sent, got, 100.0*got/max(sent,1), len(seen), tick))

trial(1, 2.0, 1)
trial(20, 2.0, 1)
trial(20, 2.0, 3)
trial(60, 2.0, 1)
out.close(); inn.close()
