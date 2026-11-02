# -*- coding: utf-8 -*-
import time, sys
from PIL import Image
import numpy as np
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh

D = r"D:\Desktop\AI 辅助对话\_shots"
print(sh("shell", "ime", "set", "com.baidu.input_mi/.ImeService")[1].strip())
time.sleep(2)
sh("shell", "input", "tap", "639", "3053")
time.sleep(2.5)
sh("shell", "screencap", "-p", "/sdcard/kbd.png")
sh("pull", "/sdcard/kbd.png", D + "\\kbd.png")

im = Image.open(D + "\\kbd.png").convert("L")
w, h = im.size
print("size", w, h)
cols = 100
# render bottom 55% (keyboard region)
y0 = int(h * 0.45)
crop = im.crop((0, y0, w, h))
rows = max(1, int(cols * (h - y0) / w / 2.1))
a = np.asarray(crop.resize((cols, rows)), dtype=np.float32)
chars = " .:-=+*#%@"
for r in range(rows):
    print("%4d|%s" % (y0 + int(r * (h - y0) / rows), "".join(chars[min(9, int((255 - a[r, c]) / 25.6))] for c in range(cols))))
