# -*- coding: utf-8 -*-
import cv2, numpy as np
cap = cv2.VideoCapture("recv_out.mp4")
stats = []
while True:
    ok, img = cap.read()
    if not ok:
        break
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    stats.append((g.mean(), g.std(), img.reshape(-1, 3).mean(axis=0)))
cap.release()
print("frames=%d" % len(stats))
print("gray mean: min=%.1f max=%.1f avg=%.1f" % (min(s[0] for s in stats), max(s[0] for s in stats), np.mean([s[0] for s in stats])))
print("gray std : min=%.1f max=%.1f avg=%.1f" % (min(s[1] for s in stats), max(s[1] for s in stats), np.mean([s[1] for s in stats])))
diffs = []
for i in range(1, len(stats)):
    diffs.append(abs(stats[i][0] - stats[i-1][0]))
print("frame-to-frame mean delta: avg=%.2f  -> %s" % (np.mean(diffs), "content changes" if np.mean(diffs) > 0.3 else "STATIC"))
b = np.mean([s[2][0] for s in stats]); g = np.mean([s[2][1] for s in stats]); r = np.mean([s[2][2] for s in stats])
print("BGR avg = %.1f %.1f %.1f  -> %s" % (b, g, r, "green garbage (decode broken)" if g > 1.6*(b+r)/2 else "plausible colour"))
print("first-frame std=%.1f last-frame std=%.1f" % (stats[0][1], stats[-1][1]))
