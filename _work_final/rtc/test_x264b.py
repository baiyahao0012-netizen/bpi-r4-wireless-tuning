# -*- coding: utf-8 -*-
import av, numpy as np
from fractions import Fraction

def mk(br):
    c = av.CodecContext.create('libx264', 'w')
    c.width, c.height, c.pix_fmt = 640, 480, 'yuv420p'
    c.time_base = Fraction(1, 30)
    c.bit_rate = br
    c.options = {'preset': 'veryfast', 'tune': 'zerolatency', 'g': '30'}
    c.open()
    return c

rng = np.random.default_rng(7)
BASE = rng.integers(0, 255, (480, 640), dtype=np.uint8)

def frame(i):
    img = np.roll(BASE, i * 3, axis=1)
    img = np.clip(img.astype(np.int16) + (i % 17), 0, 255).astype(np.uint8)
    y = img
    u = np.full((240, 320), 128, dtype=np.uint8)
    v = np.full((240, 320), 128, dtype=np.uint8)
    f = av.VideoFrame(640, 480, 'yuv420p')
    f.planes[0].update(y.tobytes())
    f.planes[1].update(u.tobytes())
    f.planes[2].update(v.tobytes())
    f.pts = i
    return f

def run(c, n, start=0):
    tot = 0
    for i in range(n):
        for pk in c.encode(frame(start + i)):
            tot += len(bytes(pk))
    return tot

for br in (500000, 2000000, 8000000):
    c = mk(br)
    n = run(c, 30)
    print("%8d bps -> %6d bytes / 30f = %.2f Mbps" % (br, n, n * 8 * 30 / 30 / 1e6))

print("--- in-place reconfig ---")
c = mk(500000)
a = run(c, 20, 0)
c.bit_rate = 8000000
b = run(c, 20, 20)
print("first 20f=%d  next 20f=%d  ratio=%.2f" % (a, b, b / a))
