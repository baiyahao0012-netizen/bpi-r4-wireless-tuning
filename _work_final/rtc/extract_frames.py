# -*- coding: utf-8 -*-
import cv2, os
p = "recv_out.mp4"
print("size", os.path.getsize(p))
cap = cv2.VideoCapture(p)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print("frames=%d  %dx%d" % (n, w, h))
picked = 0
i = 0
while True:
    ok, img = cap.read()
    if not ok:
        break
    if i in (0, n // 2, n - 1):
        fn = "frame_%02d.png" % i
        cv2.imwrite(fn, img)
        print("saved", fn, img.shape, "mean=%.1f" % img.mean())
        picked += 1
    i += 1
print("read %d frames total" % i)
cap.release()
