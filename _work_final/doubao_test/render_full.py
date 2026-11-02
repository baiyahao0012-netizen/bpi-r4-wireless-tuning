# -*- coding: utf-8 -*-
import sys
from PIL import Image
import numpy as np
path = sys.argv[1]
im = Image.open(path).convert("L")
w, h = im.size
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 100
rows = max(1, int(cols * h / w / 2.1))
a = np.asarray(im.resize((cols, rows)), dtype=np.float32)
chars = " .:-=+*#%@"
print("size", w, h)
for r in range(rows):
    print("%4d|%s" % (int(r * h / rows), "".join(chars[min(9, int((255 - a[r, c]) / 25.6))] for c in range(cols))))
