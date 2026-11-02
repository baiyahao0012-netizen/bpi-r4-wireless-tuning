# -*- coding: utf-8 -*-
"""Evidence: DNS names + per-flow ports/IPs for the phone."""
import sys, collections
from scapy.all import PcapReader, IP, TCP, UDP, DNS

PHONE = "192.168.240.219"
path = sys.argv[1]
dns_q = collections.Counter()      # query name
ip2name = collections.defaultdict(set)
flows = collections.defaultdict(lambda: [0, 0, 0, 0])  # up_pk,up_b,down_pk,down_b
n = 0
for pkt in PcapReader(path):
    n += 1
    if IP not in pkt:
        continue
    ip = pkt[IP]
    if ip.src != PHONE and ip.dst != PHONE:
        continue
    if UDP in pkt and (pkt[UDP].sport == 53 or pkt[UDP].dport == 53) and DNS in pkt:
        d = pkt[DNS]
        try:
            if d.qr == 0 and d.qd:
                dns_q[d.qd.qname.decode("utf-8", "ignore").rstrip(".")] += 1
            elif d.qr == 1 and d.qd:
                name = d.qd.qname.decode("utf-8", "ignore").rstrip(".")
                rr = d.an
                guard = 0
                while rr is not None and guard < 20:
                    try:
                        if getattr(rr, "type", None) == 1:
                            ip2name[str(rr.rdata)].add(name)
                    except Exception:
                        pass
                    rr = rr.payload if hasattr(rr, "payload") and rr.payload is not None and not isinstance(rr.payload, bytes) else None
                    guard += 1
        except Exception:
            pass
    if TCP in pkt:
        l4 = pkt[TCP]; proto = "tcp"
    elif UDP in pkt:
        l4 = pkt[UDP]; proto = "udp"
    else:
        continue
    plen = len(l4.payload)
    a = (ip.src, l4.sport); b = (ip.dst, l4.dport)
    key = (proto,) + tuple(sorted([a, b]))
    if ip.src == PHONE:
        flows[key][0] += 1; flows[key][1] += plen
    else:
        flows[key][2] += 1; flows[key][3] += plen

print("packets=%d dns_queries=%d" % (n, sum(dns_q.values())))
print("\n=== DNS queries (phone) ===")
for name, c in dns_q.most_common(30):
    print("%4d  %s" % (c, name))

rows = []
for key, v in flows.items():
    if v[3] < 3000 and v[1] < 3000:
        continue
    srv = [x for x in key[1:] if x[0] != PHONE]
    rows.append((v[3], key[0], srv[0][0] if srv else "?", srv[0][1] if srv else 0, v))
rows.sort(reverse=True)
print("\n=== top flows (by downlink bytes) ===")
print("%-16s %5s %6s %10s %10s" % ("server", "proto", "port", "down_KB", "up_KB"))
for downb, proto, sip, sport, v in rows[:25]:
    name = ",".join(sorted(ip2name.get(sip, set())))[:40]
    print("%-16s %5s %6d %10.1f %10.1f  %s" % (sip, proto, sport, downb/1e3, v[1]/1e3, name))
