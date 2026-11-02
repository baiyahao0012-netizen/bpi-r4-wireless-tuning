# -*- coding: utf-8 -*-
import time, sys
from PIL import Image
import numpy as np
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh

D = r"D:\Desktop\AI 辅助对话\_shots"
# focus input -> keyboard shows
sh("shell", "input", "tap", "639", "3053"); time.sleep(2.5)
sh("shell", "screencap", "-p", "/sdcard/rgb.png")
sh("pull", "/sdcard/rgb.png", D + "\\rgb.png")
im = Image.open(D + "\\rgb.png").convert("RGB")
a = np.asarray(im, dtype=np.float32)
h, w, _ = a.shape
print("size", w, h)
# saturation map
mx = a.max(axis=2); mn = a.min(axis=2)
sat = (mx - mn) / np.maximum(mx, 1)
# look in bottom 45%
y0 = int(h * 0.55)
region = sat[y0:]
# coarse grid 20x20 cells, find most saturated
ch, cw = 40, 80
best = []
for yy in range(0, region.shape[0]-ch, ch):
    for xx in range(0, w-cw, cw):
        cell = region[yy:yy+ch, xx:xx+cw]
        best.append((float(cell.mean()), yy+y0, xx))
best.sort(reverse=True)
print("top saturated cells (score, y, x):")
for s, yy, xx in best[:12]:
    rgb = a[yy+ch//2, xx+cw//2].astype(int)
    print("  score=%.3f  box x=%d-%d y=%d-%d  center=(%d,%d) rgb=%s" % (s, xx, xx+cw, yy, yy+ch, xx+cw//2, yy+ch//2, rgb))
