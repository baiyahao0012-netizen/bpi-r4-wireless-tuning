# -*- coding: utf-8 -*-
import sys
from PIL import Image
import numpy as np
p = sys.argv[1]
im = Image.open(p).convert('L')
w, h = im.size
print('size', w, h)
# ASCII preview ~ 64 cols
cols = 64
rows = max(1, int(cols * h / w / 2.1))
small = im.resize((cols, rows))
a = np.asarray(small, dtype=np.float32)
chars = ' .:-=+*#%@'
for y in range(rows):
    line = ''.join(chars[min(9, int((255 - a[y, x]) / 25.6))] for x in range(cols))
    print('%3d|%s' % (int(y * h / rows), line))
# row-wise dark-pixel fraction at full res
full = np.asarray(im, dtype=np.float32)
dark = (full < 110).mean(axis=1)
print('--- dark fraction by row band (each ~5% of height) ---')
band = h // 20
for i in range(20):
    seg = dark[i*band:(i+1)*band]
    print('rows %4d-%4d dark=%.3f' % (i*band, (i+1)*band, float(seg.mean())))
