# -*- coding: utf-8 -*-
"""Streaming pcap flow analyzer for the phone's traffic.
Usage: python flow_analyze.py <pcap> [phone_ip]
Prints per-flow downlink stats: bytes, duration, TTFB proxy, max gap, stalls.
"""
import sys, collections
from scapy.all import PcapReader, IP, TCP, UDP

path = sys.argv[1]
phone = sys.argv[2] if len(sys.argv) > 2 else "192.168.240.219"

# flow key = (src, sport, dst, dport, proto)
flows = collections.defaultdict(lambda: {"up": [], "down": [], "dscp": set()})
n = 0
tmin = None
for pkt in PcapReader(path):
    n += 1
    if IP not in pkt:
        continue
    ip = pkt[IP]
    if ip.src != phone and ip.dst != phone:
        continue
    t = float(pkt.time)
    if tmin is None or t < tmin:
        tmin = t
    proto = None
    if TCP in pkt:
        l4 = pkt[TCP]; proto = "tcp"
    elif UDP in pkt:
        l4 = pkt[UDP]; proto = "udp"
    else:
        continue
    key = (ip.src, l4.sport, ip.dst, l4.dport, proto)
    d = flows[key]
    d["dscp"].add(int(ip.tos) >> 2)
    plen = len(l4.payload)
    if ip.src == phone:
        d["up"].append((t, plen))
    else:
        d["down"].append((t, plen))

print("packets=%d flows=%d" % (n, len(flows)))

rows = []
for key, d in flows.items():
    up = d["up"]; down = d["down"]
    upb = sum(p for _, p in up); downb = sum(p for _, p in down)
    if downb < 2000:
        continue
    downs = [t for t, p in down if p > 0]
    if not downs:
        continue
    gaps = [b - a for a, b in zip(downs, downs[1:])]
    maxgap = max(gaps) if gaps else 0
    stalls = [g for g in gaps if g > 0.3]
    # TTFB proxy: last uplink payload time before first downlink payload
    ups = [t for t, p in up if p > 0]
    t_first_down = downs[0]
    req = [t for t in ups if t <= t_first_down]
    ttfb = t_first_down - req[-1] if req else None
    rows.append({
        "key": key, "upb": upb, "downb": downb, "t0": downs[0], "t1": downs[-1],
        "dur": downs[-1] - downs[0], "maxgap": maxgap, "nstall": len(stalls),
        "stallsum": sum(stalls), "ttfb": ttfb, "dscp": sorted(d["dscp"]),
        "nup": len(ups), "ndown": len(downs),
    })

rows.sort(key=lambda r: -r["downb"])
print("\n%-42s %9s %8s %8s %7s %5s %6s %7s %5s %s" % ("flow", "down_MB", "dur_s", "maxgap", "stall_s", "nst", "ttfb_s", "up_pk", "dn_pk", "dscp"))
for r in rows[:20]:
    k = r["key"]
    print("%-42s %9.2f %8.1f %8.2f %7.2f %5d %6s %7d %5d %s" % (
        "%s:%d>%s:%d %s" % (k[0], k[1], k[2], k[3], k[4]),
        r["downb"]/1e6, r["dur"], r["maxgap"], r["stallsum"], r["nstall"],
        ("%.2f" % r["ttfb"]) if r["ttfb"] is not None else "n/a",
        r["nup"], r["ndown"], r["dscp"]))
