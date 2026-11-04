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

rng = np.random.default_rng(11)
BASE = rng.integers(0, 255, (480, 640), dtype=np.uint8)
def frame(i):
    img = np.roll(BASE, i * 3, axis=1)
    f = av.VideoFrame(640, 480, 'yuv420p')
    f.planes[0].update(img.tobytes())
    f.planes[1].update(np.full((240,320),128,dtype=np.uint8).tobytes())
    f.planes[2].update(np.full((240,320),128,dtype=np.uint8).tobytes())
    f.pts = i
    return f
def run(c, n, start):
    tot = 0
    for i in range(n):
        for pk in c.encode(frame(start + i)):
            tot += len(bytes(pk))
    return tot

# 对照组：不变码率
c = mk(500000)
a0 = run(c, 20, 0); b0 = run(c, 20, 20)
print("CTRL  no-change : %6d -> %6d  ratio %.2f" % (a0, b0, b0/a0))

# 实验组：500k -> 8M
c = mk(500000)
a1 = run(c, 20, 0)
c.bit_rate = 8000000
b1 = run(c, 20, 20)
print("TEST  500k->8M  : %6d -> %6d  ratio %.2f" % (a1, b1, b1/a1))

# 反向：8M -> 500k
c = mk(8000000)
a2 = run(c, 20, 0)
c.bit_rate = 500000
b2 = run(c, 20, 20)
print("TEST  8M->500k  : %6d -> %6d  ratio %.2f" % (a2, b2, b2/a2))
