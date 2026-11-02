# -*- coding: utf-8 -*-
import time, sys
from PIL import Image
import numpy as np
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh

D = r"D:\Desktop\AI 辅助对话\_shots"
def shot(name):
    sh("shell", "screencap", "-p", "/sdcard/%s.png" % name)
    sh("pull", "/sdcard/%s.png" % name, D + "\\" + name + ".png")
    return np.asarray(Image.open(D + "\\" + name + ".png").convert("L"), dtype=np.int16)
def rd(A, B, x, y, w, h):
    d = np.abs(A[y:y+h, x:x+w] - B[y:y+h, x:x+w]); return float((d > 30).mean())

a = shot("s3_before")
print("tap (1260,1800)")
sh("shell", "input", "tap", "1260", "1800")
time.sleep(3.0)
b = shot("s3_after")
print("chat_area(360-2600) diff:", round(rd(a, b, 0, 360, 1440, 2240), 4))
print("inputbar(1500-1900) diff:", round(rd(a, b, 0, 1500, 1440, 400), 4))
print("keyboard(1900-3200) diff:", round(rd(a, b, 0, 1900, 1440, 1300), 4))
