# -*- coding: utf-8 -*-
"""Probe camera: default vs MJPG fourcc, measure real capture rate."""
import time, sys
import cv2

def probe(idx, fourcc, w, h, want_fps, dshow=True):
    api = cv2.CAP_DSHOW if dshow else cv2.CAP_ANY
    cap = cv2.VideoCapture(idx, api)
    if not cap.isOpened():
        return "open failed"
    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, want_fps)
    for _ in range(5):
        cap.read()
    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    reported = cap.get(cv2.CAP_PROP_FPS)
    n = 0
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 3.0:
        ok, fr = cap.read()
        if ok:
            n += 1
    el = time.perf_counter() - t0
    cap.release()
    return "fourcc=%-4s %dx%d  reported=%.1f  actual=%.1f fps" % (
        fourcc or "-", aw, ah, reported, n / el)

for fourcc in (None, "MJPG"):
    for (w, h, f) in ((640, 480, 30), (1280, 720, 30)):
        try:
            print("  " + probe(0, fourcc, w, h, f))
        except Exception as e:
            print("  fourcc=%s %dx%d ERR %s" % (fourcc, w, h, e))
