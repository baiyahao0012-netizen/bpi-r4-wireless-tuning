# -*- coding: utf-8 -*-
"""Bidirectional flow analyzer: TTFB / gaps / stalls for the phone's traffic."""
import sys, collections
from scapy.all import PcapReader, IP, TCP, UDP

PHONE = "192.168.240.219"

def analyze(path, label):
    flows = collections.defaultdict(lambda: {"up": [], "down": []})
    n = 0; t0 = None; t1 = None
    for pkt in PcapReader(path):
        n += 1
        if IP not in pkt: continue
        ip = pkt[IP]
        if ip.src != PHONE and ip.dst != PHONE: continue
        t = float(pkt.time)
        if t0 is None or t < t0: t0 = t
        if t1 is None or t > t1: t1 = t
        if TCP in pkt: l4 = pkt[TCP]; proto = "tcp"
        elif UDP in pkt: l4 = pkt[UDP]; proto = "udp"
        else: continue
        a = (ip.src, l4.sport); b = (ip.dst, l4.dport)
        key = (proto,) + tuple(sorted([a, b]))
        plen = len(l4.payload)
        if ip.src == PHONE: flows[key]["up"].append((t, plen))
        else: flows[key]["down"].append((t, plen))
    rows = []
    for key, d in flows.items():
        upb = sum(p for _, p in d["up"]); downb = sum(p for _, p in d["down"])
        downs = [t for t, p in d["down"] if p > 0]
        if not downs or downb < 3000: continue
        gaps = [b - a for a, b in zip(downs, downs[1:])]
        maxgap = max(gaps) if gaps else 0
        stalls = [g for g in gaps if g > 0.3]
        ups = [t for t, p in d["up"] if p > 0]
        d0 = downs[0]
        prev = [t for t in ups if t <= d0]
        ttfb = (d0 - prev[-1]) if prev else None
        # server side = the endpoint that is not the phone
        srv = [x for x in key[1:] if x[0] != PHONE]
        srv_ip = srv[0][0] if srv else "?"
        rows.append(dict(srv=srv_ip, proto=key[0], upb=upb, downb=downb,
                         dur=downs[-1]-downs[0], maxgap=maxgap, nstall=len(stalls),
                         stallsum=sum(stalls), ttfb=ttfb, ndown=len(downs)))
    rows.sort(key=lambda r: -r["downb"])
    print("\n===== %s ===== packets=%d span=%.1fs flows_with_dl=%d" % (label, n, (t1-t0) if t0 else 0, len(rows)))
    print("%-16s %4s %9s %8s %7s %7s %5s %8s" % ("server", "proto", "down_KB", "dur_s", "maxgap", "stall_s", "nst", "ttfb_s"))
    for r in rows[:12]:
        print("%-16s %4s %9.0f %8.1f %7.2f %7.2f %5d %8s" % (
            r["srv"], r["proto"], r["downb"]/1e3, r["dur"], r["maxgap"], r["stallsum"], r["nstall"],
            ("%.2f" % r["ttfb"]) if r["ttfb"] is not None else "n/a"))
    tot_down = sum(r["downb"] for r in rows)
    tot_stall = sum(r["stallsum"] for r in rows)
    tot_n = sum(r["nstall"] for r in rows)
    print("TOTAL down=%.1f KB  stalls>300ms=%d  stall_time=%.1fs" % (tot_down/1e3, tot_n, tot_stall))
    return rows

if __name__ == "__main__":
    analyze(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
