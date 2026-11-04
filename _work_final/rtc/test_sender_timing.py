# -*- coding: utf-8 -*-
"""Replicate sender.py's loop exactly, but time every stage."""
import time
from fractions import Fraction
import cv2, av
import rtc2, l2sock


class Pacer(object):
    def __init__(self, bps):
        self.bps = float(bps) * 1.3
        self.next_t = time.perf_counter()
        self.sent = 0
    def wait(self, nbytes):
        now = time.perf_counter()
        if self.next_t < now:
            self.next_t = now
        self.next_t += nbytes * 8.0 / self.bps
        self.sent += nbytes
        d = self.next_t - time.perf_counter()
        if d > 0.0005:
            time.sleep(d)


def is_key(pkt):
    try:
        return bool(pkt.is_keyframe)
    except Exception:
        pass
    b = bytes(pkt)
    i = 0
    while i + 4 < len(b):
        if b[i] == 0 and b[i+1] == 0 and b[i+2] == 1:
            t = b[i+3] & 0x1F
            if t in (5, 7):
                return True
            i += 3
        else:
            i += 1
    return False


W, H, FPS, BR = 640, 480, 30, 2000000
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
cap.set(cv2.CAP_PROP_FPS, FPS)

enc = av.CodecContext.create('libx264', 'w')
enc.width, enc.height, enc.pix_fmt = W, H, 'yuv420p'
enc.time_base = Fraction(1, FPS)
enc.bit_rate = BR
enc.options = {'preset': 'veryfast', 'tune': 'zerolatency',
               'g': str(FPS*2), 'sc_threshold': '0'}
enc.open()

sock = l2sock.L2Socket(dev_substr="GbE Family")
dst = l2sock.mac_to_bytes("C0-35-32-19-CC-FB")
src = l2sock.mac_to_bytes("40-C2-BA-52-70-95")
pacer = Pacer(BR)

acc = dict(read=0.0, conv=0.0, enc=0.0, key=0.0, chunk=0.0, send=0.0, pace=0.0, tail=0.0)
n = 0
seq = 0
fid = 0
nb = 0
t0 = time.perf_counter()
next_frame_t = t0
while time.perf_counter() - t0 < 6.0:
    a = time.perf_counter(); ok, img = cap.read(); b = time.perf_counter()
    if not ok:
        continue
    vf = av.VideoFrame.from_ndarray(img, format='bgr24').reformat(format='yuv420p')
    c = time.perf_counter()
    vf.pts = fid; vf.time_base = Fraction(1, FPS)
    pkts = enc.encode(vf)
    d = time.perf_counter()
    for pkt in pkts:
        data = bytes(pkt)
        if not data:
            continue
        e = time.perf_counter(); kf = is_key(pkt); f = time.perf_counter()
        chunks, seq = rtc2.chunk_frame(data, fid, 0, 0, seq, keyframe=kf,
                                       chunk_size=rtc2.DEFAULT_CHUNK)
        g = time.perf_counter()
        for ch in chunks:
            wire = dst + src + b"\x88\xb5" + ch
            h = time.perf_counter()
            try:
                sock.send(wire)
            except Exception:
                pass
            i2 = time.perf_counter()
            pacer.wait(len(ch) + 14)
            j = time.perf_counter()
            acc['send'] += i2 - h; acc['pace'] += j - i2
            nb += len(ch) + 14
        acc['key'] += f - e; acc['chunk'] += g - f
    acc['read'] += b - a; acc['conv'] += c - b; acc['enc'] += d - c
    fid += 1; n += 1
    next_frame_t += 1.0 / FPS
    t = time.perf_counter()
    dd = next_frame_t - t
    if dd > 0:
        time.sleep(dd)
    else:
        next_frame_t = time.perf_counter()
    acc['tail'] += time.perf_counter() - t

el = time.perf_counter() - t0
sock.close(); cap.release()
tot = sum(acc.values())
print("frames=%d  fps=%.1f  %.2f Mbps" % (n, n/el, nb*8/el/1e6))
for k in ('read','conv','enc','key','chunk','send','pace','tail'):
    print("  %-6s %7.2f ms/frame  (%.0f%%)" % (k, acc[k]/n*1000, 100*acc[k]/tot))
print("  TOTAL  %7.2f ms/frame  -> ceiling %.1f fps" % (tot/n*1000, n/tot))
