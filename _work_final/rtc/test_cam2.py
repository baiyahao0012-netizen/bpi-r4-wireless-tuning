# -*- coding: utf-8 -*-
"""Is the camera itself now slow? auto vs manual short exposure."""
import time
import cv2

def bench(cap, secs=3.0):
    for _ in range(3):
        cap.read()
    n = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < secs:
        ok, fr = cap.read()
        if ok:
            n += 1
    return n / (time.perf_counter() - t0)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

print("auto-exposure fps = %.1f" % bench(cap))
print("  reported FPS prop = %.1f" % cap.get(cv2.CAP_PROP_FPS))
print("  CAP_PROP_EXPOSURE = %.3f  AUTO = %.3f"
      % (cap.get(cv2.CAP_PROP_EXPOSURE), cap.get(cv2.CAP_PROP_AUTO_EXPOSURE)))
ok, fr = cap.read()
print("  frame mean brightness = %.1f" % (fr.mean() if ok else -1))

for auto, exp in ((0.25, -6), (0.25, -5), (0.25, -4)):
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto)
    cap.set(cv2.CAP_PROP_EXPOSURE, exp)
    f = bench(cap)
    ok, fr = cap.read()
    print("manual auto=%.2f exp=%d -> fps=%.1f  brightness=%.1f"
          % (auto, exp, f, fr.mean() if ok else -1))

cap.release()
print("\n== now the full send chain again ==")
