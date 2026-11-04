# -*- coding: utf-8 -*-
import av, sys
from fractions import Fraction
print("PyAV", av.__version__)

def mk(br, preset='veryfast'):
    c = av.CodecContext.create('libx264', 'w')
    c.width, c.height, c.pix_fmt = 640, 480, 'yuv420p'
    c.time_base = Fraction(1, 30)
    c.bit_rate = br
    c.options = {'preset': preset, 'tune': 'zerolatency', 'g': '30'}
    c.open()
    return c

def run(c, n, start=0):
    tot = 0
    for i in range(n):
        f = av.VideoFrame(640, 480, 'yuv420p')
        for p in f.planes:
            p.update(bytes([(16 + ((i * 7 + start) % 200))] * p.buffer_size))
        f.pts = start + i
        for pk in c.encode(f):
            tot += len(bytes(pk))
    return tot

# baseline: 2M vs 8M
c2 = mk(2000000); b2 = run(c2, 30)
c8 = mk(8000000); b8 = run(c8, 30)
print("2Mbps 30f -> %d bytes" % b2)
print("8Mbps 30f -> %d bytes" % b8)

# in-place reconfig attempt
c = mk(2000000)
a = run(c, 15, 0)
before = c.bit_rate
try:
    c.bit_rate = 8000000
    ok = True
except Exception as e:
    ok = repr(e)
b = run(c, 15, 15)
print("in-place reconfig supported attr-set:", ok, "| attr now:", c.bit_rate)
print("first 15f: %d bytes, next 15f: %d bytes  (ratio %.2f)" % (a, b, (b / a) if a else 0))

# reopen approach
c_a = mk(2000000); x1 = run(c_a, 15, 0)
c_b = mk(8000000); x2 = run(c_b, 15, 15)
print("reopen: 2M 15f=%d  8M 15f=%d  ratio %.2f" % (x1, x2, (x2 / x1) if x1 else 0))
