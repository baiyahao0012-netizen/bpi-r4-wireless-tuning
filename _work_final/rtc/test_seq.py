# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, ".")
from sender import SeqGen

g = SeqGen()
g._n = 0xFFF0          # 16 chunks before the wrap
maxspan = True
bad = 0
for i in range(200):
    s = g.reserve(8)
    if s + 8 - 1 > 0xFFFF:
        bad += 1
        print("BAD reservation: start=%d end=%d" % (s, s + 7))
print("reservations=200  overflow=%d" % bad)
print("final counter=%d" % g._n)
