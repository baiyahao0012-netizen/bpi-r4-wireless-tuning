# -*- coding: utf-8 -*-
# ac_udp_recv.py <duration_s> <out_csv>
import socket, select, time, sys, csv

dur = float(sys.argv[1])
out = sys.argv[2]
ports = [(6001, 'vo'), (6002, 'bk')]
socks = []
for port, tag in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16 * 1024 * 1024)
    s.bind(('0.0.0.0', port))
    s.setblocking(False)
    socks.append((s, tag))
fd_to_tag = {s.fileno(): tag for s, tag in socks}

counts = {'vo': 0, 'bk': 0}
t0 = time.monotonic()
next_t = t0 + 0.1
rows = []
while True:
    now = time.monotonic()
    if now - t0 >= dur:
        break
    r, _, _ = select.select([s for s, _ in socks], [], [], 0.005)
    for s in r:
        tag = fd_to_tag[s.fileno()]
        while True:
            try:
                data = s.recv(65535)
            except BlockingIOError:
                break
            counts[tag] += len(data)
    now = time.monotonic()
    if now >= next_t:
        rows.append((round(now - t0, 3),
                     counts['vo'] * 8.0 / 1e6 / 0.1,
                     counts['bk'] * 8.0 / 1e6 / 0.1))
        counts = {'vo': 0, 'bk': 0}
        next_t += 0.1

with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['elapsed_s', 'vo_mbps', 'bk_mbps'])
    for row in rows:
        w.writerow(['%.3f' % row[0], '%.1f' % row[1], '%.1f' % row[2]])
print('wrote', out, 'rows', len(rows))
