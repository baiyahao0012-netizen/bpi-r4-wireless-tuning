# -*- coding: utf-8 -*-
"""Does the Npcap capture path inflate measured one-way latency?

Receives the same UDP stream twice: once from a kernel socket and once from an
Npcap capture on the Wi-Fi adapter, then compares arrival-relative latency for
the very same datagrams (matched by their RTC2 send_ts_us).
"""
import socket, struct, threading, time
import l2sock, rtc2

PORT = 9911
sock_lat = {}
cap_lat = {}
stop = threading.Event()


def capture():
    s = l2sock.L2Socket(dev_substr='8852', direction=l2sock.PCAP_D_IN)
    while not stop.is_set():
        r = s.recv(0.2)
        if not r:
            continue
        ts, raw = r
        t_got = time.perf_counter()   # userspace delivery time, not pcap epoch
        if len(raw) < 42 or raw[12:14] != b'\x08\x00':
            continue
        ihl = (raw[14] & 0x0F) * 4
        if raw[14 + 9] != 17:
            continue
        u = 14 + ihl
        if struct.unpack('!H', raw[u + 2:u + 4])[0] != PORT:
            continue
        try:
            h = rtc2.unpack_header(raw[u + 8:])
        except Exception:
            continue
        d = (int(t_got * 1e6) - h['send_ts_us']) & 0xFFFFFFFF
        if d < 5000000:
            cap_lat[(h['frame_id'], h['chunk_idx'])] = d / 1000.0
    s.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
    s.bind(('', PORT))
    s.settimeout(0.05)
    threading.Thread(target=capture, daemon=True).start()
    t_end = time.perf_counter() + 13.0
    while time.perf_counter() < t_end:
        try:
            data, _ = s.recvfrom(65535)
        except socket.timeout:
            continue
        now = time.perf_counter()
        try:
            h = rtc2.unpack_header(data)
        except Exception:
            continue
        d = (int(now * 1e6) - h['send_ts_us']) & 0xFFFFFFFF
        if d < 5000000:
            sock_lat[(h['frame_id'], h['chunk_idx'])] = d / 1000.0
    stop.set()
    time.sleep(0.3)

    def pct(v, p):
        s2 = sorted(v)
        return s2[min(len(s2) - 1, int(len(s2) * p / 100.0))]

    common = [k for k in sock_lat if k in cap_lat]
    print("socket datagrams=%d  capture datagrams=%d  matched=%d"
          % (len(sock_lat), len(cap_lat), len(common)))
    if common:
        a = [sock_lat[k] for k in common]
        b = [cap_lat[k] for k in common]
        diff = sorted(bb - aa for aa, bb in zip(a, b))
        print("kernel socket latency ms: p50=%.1f p95=%.1f p99=%.1f" %
              (pct(a, 50), pct(a, 95), pct(a, 99)))
        print("npcap  capture latency ms: p50=%.1f p95=%.1f p99=%.1f" %
              (pct(b, 50), pct(b, 95), pct(b, 99)))
        print("npcap - socket ms: p50=%.1f p95=%.1f  (capture-path overhead)"
              % (pct(diff, 50), pct(diff, 95)))


main()
