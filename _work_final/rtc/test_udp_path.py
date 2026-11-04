# -*- coding: utf-8 -*-
"""Which UDP destination actually crosses the radio?  unicast-to-local vs broadcast."""
import socket, struct, threading, time
import l2sock

PORT = 9911
seen = {'wifi': 0, 'eth': 0}
stop = threading.Event()

def sniff(dev, key):
    try:
        s = l2sock.L2Socket(dev_substr=dev, direction=l2sock.PCAP_D_IN)
    except Exception as e:
        print("sniff %s failed: %r" % (dev, e))
        return
    while not stop.is_set():
        r = s.recv(0.2)
        if not r:
            continue
        raw = r[1]
        if len(raw) < 42 or raw[12:14] != b'\x08\x00':
            continue
        ihl = (raw[14] & 0x0F) * 4
        if raw[14 + 9] != 17:
            continue
        u = 14 + ihl
        if len(raw) < u + 8:
            continue
        dport = struct.unpack('!H', raw[u + 2:u + 4])[0]
        if dport == PORT:
            seen[key] += 1
    s.close()

rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
rx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
rx.bind(('', PORT))
rx.settimeout(0.4)

ts = [threading.Thread(target=sniff, args=('8852', 'wifi'), daemon=True),
      threading.Thread(target=sniff, args=('GbE', 'eth'), daemon=True)]
for x in ts:
    x.start()
time.sleep(0.5)

tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
tx.bind(('192.168.240.2', 0))

for label, dst in (('unicast 192.168.240.147', '192.168.240.147'),
                   ('broadcast 192.168.240.255', '192.168.240.255')):
    seen['wifi'] = seen['eth'] = 0
    got = 0
    for i in range(20):
        try:
            tx.sendto(b'X' * 200, (dst, PORT))
        except Exception as e:
            print("  send failed:", e)
            break
        time.sleep(0.005)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 0.8:
        try:
            rx.recvfrom(2048)
            got += 1
        except socket.timeout:
            pass
    time.sleep(0.2)
    print("%-30s app_received=%2d/20  on_wifi=%2d  on_eth=%2d"
          % (label, got, seen['wifi'], seen['eth']))

stop.set()
tx.close(); rx.close()
