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

a = shot("s2_before")
print("tap send button (1332,2866)")
sh("shell", "input", "tap", "1332", "2866")
time.sleep(2.5)
b = shot("s2_after")
print("chat_area diff:", round(rd(a, b, 0, 360, 1440, 2350), 4))
print("input_box diff:", round(rd(a, b, 206, 2967, 866, 172), 4))
print("keyboard gone?  kbd_region diff:", round(rd(a, b, 0, 2000, 1440, 1200), 4))
