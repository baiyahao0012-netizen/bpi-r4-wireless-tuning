#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rtp_probe.py — 最小 RTP 头探针（测量工具，不参与媒体收发）

监听一个 UDP 端口，把收到的每个包按 RTP 规范拆开 12 字节固定头，
统计包数、载荷字节数、序号缺口、SSRC 集合、时间戳个数，最后输出 JSON。

它是"计量器"：只读数、不打包、不解码、不参与任何媒体路径。
被测的媒体层是 GStreamer 的 rtph264pay / rtpopuspay，不是本脚本。

用法：python3 rtp_probe.py [端口] [监听秒数]
"""

import json
import socket
import struct
import sys
import time

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5004
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", port))
s.settimeout(0.5)

n = 0
payload_bytes = 0
first = None
last = None
ssrcs = set()
pts = set()
seq_gaps = 0
prev = None

end = time.time() + duration

while time.time() < end:
    try:
        data, _ = s.recvfrom(65535)
    except socket.timeout:
        continue

    if len(data) < 12:
        continue

    v = data[0] >> 6
    if v != 2:
        continue

    pt = data[1] & 0x7F
    seq = struct.unpack("!H", data[2:4])[0]
    ts = struct.unpack("!I", data[4:8])[0]
    ssrc = struct.unpack("!I", data[8:12])[0]

    if prev is not None and ((seq - prev) & 0xFFFF) not in (0, 1):
        seq_gaps += 1
    prev = seq

    n += 1
    payload_bytes += len(data) - 12
    ssrcs.add(ssrc)
    pts.add(ts)

    if first is None:
        first = (seq, ts, ssrc, pt, len(data))
    last = (seq, ts, ssrc, pt, len(data))

s.close()

print(json.dumps({
    "port": port,
    "packets": n,
    "payload_bytes": payload_bytes,
    "seq_gaps": seq_gaps,
    "ssrcs": sorted(ssrcs),
    "timestamps": len(pts),
    "first": first,
    "last": last,
}, ensure_ascii=False))
