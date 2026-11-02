# -*- coding: utf-8 -*-
import sys, av
import numpy as np
from PIL import Image
path = sys.argv[1]
times = [float(x) for x in sys.argv[2].split(",")]
y0f, y1f = float(sys.argv[3]), float(sys.argv[4])
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 64
c = av.open(path); vs = c.streams.video[0]
targets = sorted(times); ti = 0
chars = " .:-=+*#%@"
for f in c.decode(vs):
    t = f.time if f.time is not None else float(f.pts * vs.time_base)
    if ti >= len(targets): break
    if t >= targets[ti]:
        g = np.asarray(f.to_ndarray(format="gray"), dtype=np.uint8)
        h, w = g.shape
        yy0, yy1 = int(h*y0f), int(h*y1f)
        crop = g[yy0:yy1]
        rows = max(1, int(cols * crop.shape[0] / w / 2.1))
        s = np.asarray(Image.fromarray(crop).resize((cols, rows)), dtype=np.float32)
        print("\n== t=%.2f (want %.1f) crop y %d-%d ==" % (t, targets[ti], yy0, yy1))
        for r in range(rows):
            print("%4d|%s" % (yy0 + int(r * crop.shape[0] / rows), "".join(chars[min(9, int((255 - s[r, cc]) / 25.6))] for cc in range(cols))))
        ti += 1
