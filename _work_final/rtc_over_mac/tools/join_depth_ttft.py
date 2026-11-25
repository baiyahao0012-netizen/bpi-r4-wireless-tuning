#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Join server/client ledgers and correlate queue depth at request arrival with TTFT."""
import json
import sys
import os
import statistics


def load(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            out[r["mid"]] = r
    return out


def main(d):
    names = sorted(f[:-10] for f in os.listdir(d) if f.endswith("_srv.jsonl"))
    for arm in names:
        s = load(os.path.join(d, arm + "_srv.jsonl"))
        c = load(os.path.join(d, arm + "_cli.jsonl"))
        pairs = []
        for mid, sr in s.items():
            cr = c.get(mid)
            if cr and cr.get("ttft_us") is not None:
                pairs.append((sr.get("qdepth_at_recv", 0), cr["ttft_us"]))
        if not pairs:
            print("%-9s no pairs" % arm)
            continue
        depths = [p[0] for p in pairs]
        ttfts = [p[1] for p in pairs]
        # rank correlation (Spearman) without scipy
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i])
            r = [0] * len(v)
            for pos, i in enumerate(order):
                r[i] = pos
            return r
        rx, ry = rank(depths), rank(ttfts)
        n = len(pairs)
        mx, my = sum(rx) / n, sum(ry) / n
        cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
        vx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
        vy = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
        rho = cov / (vx * vy) if vx and vy else 0
        print("%-9s n=%2d depth p50=%4d mean=%6.1f  ttft p50=%8.1f ms  spearman=%.2f" %
              (arm, n, statistics.median(depths), statistics.mean(depths),
               statistics.median(ttfts) / 1000.0, rho))
        sample = sorted(pairs, key=lambda p: p[0])[:3] + sorted(pairs, key=lambda p: -p[0])[:3]
        print("          sample(depth,ttft_ms): " +
              ", ".join("%d/%.1f" % (a, b / 1000.0) for a, b in sample))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
