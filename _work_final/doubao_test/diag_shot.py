# -*- coding: utf-8 -*-
import subprocess, time, sys
from PIL import Image
import numpy as np
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh

D = r"D:\Desktop\AI 辅助对话\_shots"

def shot(name):
    sh("shell", "screencap", "-p", "/sdcard/%s.png" % name)
    sh("pull", "/sdcard/%s.png" % name, D + "\\" + name + ".png")
    return np.asarray(Image.open(D + "\\" + name + ".png").convert("L"), dtype=np.int16)

a = shot("in_before")
sh("shell", "input", "tap", "639", "3053"); time.sleep(1.2)
b = shot("in_aftertap")
sh("shell", "input text 'hello12345'"); time.sleep(1.5)
c = shot("in_aftertype")

def region_diff(x, y, w, h, A, B):
    d = np.abs(A[y:y+h, x:x+w] - B[y:y+h, x:x+w])
    return float((d > 30).mean())

# input box region and action area (send button zone)
for label, (x, y, w, h) in {
    "input_box": (206, 2967, 866, 172),
    "action_area": (1072, 2949, 324, 207),
    "chat_area": (0, 360, 1440, 2300),
}.items():
    print("%-12s before->tap=%.4f  tap->type=%.4f" % (
        label, region_diff(x, y, w, h, a, b), region_diff(x, y, w, h, b, c)))
print("image shape", a.shape)
