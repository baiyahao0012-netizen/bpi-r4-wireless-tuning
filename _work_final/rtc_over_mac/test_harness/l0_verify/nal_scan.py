#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nal_scan.py — 扫描 annexb H.264 文件的 NAL 类型分布（只读统计）"""
import collections
import sys

data = open(sys.argv[1], "rb").read()
nals = []
i, n = 0, len(data)
while i < n - 3:
    if data[i:i+4] == b"\x00\x00\x00\x01":
        hdr = data[i+4] if i+4 < n else 0
        nals.append(hdr & 0x1F)
        i += 4
    elif data[i:i+3] == b"\x00\x00\x01":
        hdr = data[i+3] if i+3 < n else 0
        nals.append(hdr & 0x1F)
        i += 3
    else:
        i += 1

c = collections.Counter(nals)
print(sys.argv[1])
print("  nals=%d types=%s" % (len(nals), dict(sorted(c.items()))))
print("  first20=%s" % nals[:20])
print("  SPS(7)=%d PPS(8)=%d IDR(5)=%d" % (c[7], c[8], c[5]))
