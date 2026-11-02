# -*- coding: utf-8 -*-
import subprocess, time, sys, xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
sys.path.insert(0, r"D:\Desktop\AI 辅助对话\_work_final\doubao_test")
from recon_send import sh, dump_ui, parse

D = r"D:\Desktop\AI 辅助对话\_shots"
def shot(name):
    sh("shell", "screencap", "-p", "/sdcard/%s.png" % name)
    sh("pull", "/sdcard/%s.png" % name, D + "\\" + name + ".png")
    return np.asarray(Image.open(D + "\\" + name + ".png").convert("L"), dtype=np.int16)

def rd(A, B, x, y, w, h):
    d = np.abs(A[y:y+h, x:x+w] - B[y:y+h, x:x+w])
    return float((d > 30).mean())

a = shot("send_before")
print("press ENTER (keyevent 66)")
sh("shell", "input", "keyevent", "66")
time.sleep(3.0)
b = shot("send_after")
print("chat_area diff:", round(rd(a, b, 0, 360, 1440, 2300), 4))
print("input_box diff:", round(rd(a, b, 206, 2967, 866, 172), 4))
p = dump_ui(); parse(p, D + "\\ui_send.txt")
with open(D + "\\ui_send.txt", encoding="utf-8") as f:
    for line in f:
        if "message" in line.lower() or "input_text" in line or "bubble" in line.lower():
            print(line.rstrip()[:160])
