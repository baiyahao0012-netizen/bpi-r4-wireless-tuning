# -*- coding: utf-8 -*-
import av, numpy as np
from fractions import Fraction

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

def mk_vbv(br):
    c = av.CodecContext.create('libx264', 'w')
    c.width, c.height, c.pix_fmt = 640, 480, 'yuv420p'
    c.time_base = Fraction(1, 30)
    c.bit_rate = br
    try: c.rc_max_rate = br
    except Exception as e: print("rc_max_rate set fail:", e)
    try: c.rc_buffer_size = br // 2
    except Exception as e: print("rc_buffer_size set fail:", e)
    c.options = {'preset': 'veryfast', 'tune': 'zerolatency', 'g': '30'}
    c.open()
    return c

c = mk_vbv(500000)
a = run(c, 20, 0)
c.bit_rate = 8000000
try: c.rc_max_rate = 8000000
except Exception: pass
b = run(c, 20, 20)
print("VBV 500k->8M : %6d -> %6d  ratio %.2f" % (a, b, b / a))
print("attrs: bit_rate=%s rc_max_rate=%s rc_buffer_size=%s" % (
    getattr(c, 'bit_rate', '?'), getattr(c, 'rc_max_rate', '?'), getattr(c, 'rc_buffer_size', '?')))
