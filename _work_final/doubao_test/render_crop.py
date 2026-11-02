# -*- coding: utf-8 -*-
import sys
from PIL import Image
import numpy as np

def render(path, x, y, w, h, cols=96, label=""):
    im = Image.open(path).convert("L").crop((x, y, x+w, y+h))
    rows = max(1, int(cols * h / w / 2.1))
    a = np.asarray(im.resize((cols, rows)), dtype=np.float32)
    print("--- %s %s crop(%d,%d,%d,%d) ---" % (label, path.split("\\")[-1], x, y, w, h))
    chars = " .:-=+*#%@"
    for r in range(rows):
        print("".join(chars[min(9, int((255 - a[r, c]) / 25.6))] for c in range(cols)))

D = r"D:\Desktop\AI 辅助对话\_shots"
render(D + "\\in_aftertype.png", 0, 2900, 1440, 300, 100, "INPUT-AREA after typing")
render(D + "\\in_before.png", 0, 2900, 1440, 300, 100, "INPUT-AREA before")
