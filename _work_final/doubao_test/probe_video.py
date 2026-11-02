# -*- coding: utf-8 -*-
import sys, av
from PIL import Image
import numpy as np

path = sys.argv[1]
c = av.open(path)
vs = c.streams.video[0]
print("codec:", vs.codec_context.name, "size:", vs.codec_context.width, "x", vs.codec_context.height)
print("fps:", float(vs.average_rate), "frames:", vs.frames, "duration(s):", float(vs.duration * vs.time_base) if vs.duration else "?")
print("container duration:", float(c.duration / av.time_base) if c.duration else "?")
n = 0
samples = []
for frame in c.decode(vs):
    if n % 60 == 0:
        arr = frame.to_ndarray(format="rgb24")
        samples.append((n, float(frame.pts * vs.time_base), arr))
    n += 1
print("decoded frames:", n)
# render a couple of samples as ASCII (downscaled)
for idx, t, arr in samples[:2] + samples[-2:]:
    g = np.asarray(Image.fromarray(arr).convert("L").resize((90, 100)), dtype=np.float32)
    chars = " .:-=+*#%@"
    print("=== frame %d t=%.1fs ===" % (idx, t))
    for r in range(g.shape[0]):
        print("".join(chars[min(9, int((255 - g[r, c]) / 25.6))] for c in range(g.shape[1])))
