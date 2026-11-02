# -*- coding: utf-8 -*-
import sys, av
import numpy as np
from PIL import Image

path = sys.argv[1]
times = [float(x) for x in sys.argv[2].split(",")]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 70
c = av.open(path); vs = c.streams.video[0]
targets = sorted(times)
ti = 0
chars = " .:-=+*#%@"
for f in c.decode(vs):
    t = f.time if f.time is not None else float(f.pts * vs.time_base)
    if ti >= len(targets): break
    if t >= targets[ti]:
        g = np.asarray(f.to_ndarray(format="gray"), dtype=np.uint8)
        h, w = g.shape
        rows = max(1, int(cols * h / w / 2.1))
        s = np.asarray(Image.fromarray(g).resize((cols, rows)), dtype=np.float32)
        print("\n===== t=%.2fs  (requested %.2f) =====" % (t, targets[ti]))
        for r in range(rows):
            print("%4d|%s" % (int(r * h / rows), "".join(chars[min(9, int((255 - s[r, cc]) / 25.6))] for cc in range(cols))))
        ti += 1
