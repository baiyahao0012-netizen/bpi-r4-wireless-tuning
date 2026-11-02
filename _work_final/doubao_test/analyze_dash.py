# -*- coding: utf-8 -*-
import json, sys, urllib.request, statistics

url = "http://127.0.0.1:8099/api/stats"
d = json.load(urllib.request.urlopen(url, timeout=30))
h = d.get("hist", {})
t = h.get("t", []); ttfb = h.get("ttfb", []); ef = h.get("ef", []); aidl = h.get("aidl", [])
n = min(len(t), len(ttfb), len(ef), len(aidl))
t, ttfb, ef, aidl = t[:n], ttfb[:n], ef[:n], aidl[:n]

# split at first EF>0 (accel turned on)
on_idx = None
for i, v in enumerate(ef):
    if v and v > 0.01:
        on_idx = i; break

def stat(vals):
    v = [x for x in vals if x is not None]
    if not v: return None
    v = sorted(v)
    return {"n": len(v), "mean": sum(v)/len(v), "p50": v[len(v)//2],
            "p90": v[int(len(v)*0.9)], "max": v[-1]}

print("samples=%d  accel_now=%s  split_at=%s" % (n, d.get("accel"), ("idx %d (%s)" % (on_idx, t[on_idx])) if on_idx is not None else "no EF>0"))
if on_idx is None:
    print("no acceleration segment found in the current 60s window")
    sys.exit()

pre_ttfb = [ttfb[i] for i in range(on_idx) if ttfb[i] is not None]
post_ttfb = [ttfb[i] for i in range(on_idx, n) if ttfb[i] is not None]
pre_dl = [aidl[i] for i in range(on_idx)]
post_dl = [aidl[i] for i in range(on_idx, n)]
pre_ef = [ef[i] for i in range(on_idx)]
post_ef = [ef[i] for i in range(on_idx, n)]

print("\n== BEFORE accel ==")
print(" TTFB:", stat(pre_ttfb))
print(" AI downlink mean KB/s: %.2f" % (sum(pre_dl)/len(pre_dl) if pre_dl else 0))
print(" EF KB/s: %.2f" % (sum(pre_ef)/len(pre_ef) if pre_ef else 0))
print("\n== AFTER accel ==")
print(" TTFB:", stat(post_ttfb))
print(" AI downlink mean KB/s: %.2f" % (sum(post_dl)/len(post_dl) if post_dl else 0))
print(" EF KB/s: %.2f" % (sum(post_ef)/len(post_ef) if post_ef else 0))
