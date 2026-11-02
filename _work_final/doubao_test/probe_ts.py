# -*- coding: utf-8 -*-
import av, sys, collections
c = av.open(sys.argv[1]); vs = c.streams.video[0]
print("time_base:", vs.time_base, "avg_rate:", vs.average_rate)
ts = []
for i, f in enumerate(c.decode(vs)):
    t = f.time if f.time is not None else float(f.pts * vs.time_base)
    ts.append((i, f.pts, t, f.pict_type))
print("frames:", len(ts))
print("first 8:", [(i, p, round(t,3)) for i,p,t,_ in ts[:8]])
print("last 5:", [(i, p, round(t,3)) for i,p,t,_ in ts[-5:]])
print("non-monotonic:", sum(1 for a,b in zip(ts, ts[1:]) if b[2] < a[2]))
print("top deltas:", collections.Counter(round(b[2]-a[2],3) for a,b in zip(ts, ts[1:])).most_common(8))
print("pict types:", dict(collections.Counter(p for _,_,_,p in ts)))
print("min/max t:", min(t for _,_,t,_ in ts), max(t for _,_,t,_ in ts))
