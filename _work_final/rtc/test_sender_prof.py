# -*- coding: utf-8 -*-
"""Profile the capture->encode->send chain to find the fps bottleneck."""
import time, cv2, av
from fractions import Fraction

W, H, FPS, BR = 640, 480, 30, 2000000
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
cap.set(cv2.CAP_PROP_FPS, FPS)
for _ in range(5):
    cap.read()

enc = av.CodecContext.create('libx264', 'w')
enc.width, enc.height, enc.pix_fmt = W, H, 'yuv420p'
enc.time_base = Fraction(1, FPS)
enc.bit_rate = BR
enc.options = {'preset': 'veryfast', 'tune': 'zerolatency',
               'g': str(FPS * 2), 'sc_threshold': '0'}
enc.open()

tr = tc = te = 0.0
n = 0
nbytes = 0
t0 = time.perf_counter()
while time.perf_counter() - t0 < 5.0:
    a = time.perf_counter()
    ok, img = cap.read()
    b = time.perf_counter()
    if not ok:
        continue
    vf = av.VideoFrame.from_ndarray(img, format='bgr24').reformat(format='yuv420p')
    c = time.perf_counter()
    vf.pts = n
    vf.time_base = Fraction(1, FPS)
    for p in enc.encode(vf):
        nbytes += len(bytes(p))
    d = time.perf_counter()
    tr += b - a; tc += c - b; te += d - c; n += 1
el = time.perf_counter() - t0
print("frames=%d  achieved_fps=%.1f" % (n, n / el))
print("  read    %.2f ms/frame" % (tr / n * 1000))
print("  convert %.2f ms/frame" % (tc / n * 1000))
print("  encode  %.2f ms/frame" % (te / n * 1000))
print("  total   %.2f ms/frame -> ceiling %.1f fps" % ((tr + tc + te) / n * 1000, n / (tr + tc + te)))
print("  bytes/frame = %d -> %.2f Mbps at %.1f fps" % (nbytes // n, nbytes * 8 / el / 1e6, n / el))
