#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rtcp_probe.py — 最小 RTCP 探针（测量工具，不参与媒体收发）

RTCP 包同样以版本 2 开头，但第 2 字节低 5 位是 RTCP 报文类型：
  200 = SR（发送方报告，携带 NTP<->RTP 时间映射，音画同步锚点）
  201 = RR（接收方报告）
  202 = SDES；203 = BYE；204 = APP；205 = RTPFB（含 NACK）；206 = PSFB（含 PLI）

用法：python3 rtcp_probe.py [端口] [监听秒数]
输出 JSON：包总数 + 各 RTCP 类型计数。
"""

import json
import socket
import sys
import time

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5035
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 14.0

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", port))
s.settimeout(0.5)

n = 0
pt_counts = {}
end = time.time() + duration

while time.time() < end:
    try:
        data, _ = s.recvfrom(65535)
    except socket.timeout:
        continue
    if len(data) < 8:
        continue
    if data[0] >> 6 != 2:
        continue
    pt = data[1]  # RTCP PT 是整字节（200 SR / 201 RR / 205 RTPFB / 206 PSFB），不取低 5 位
    n += 1
    pt_counts[str(pt)] = pt_counts.get(str(pt), 0) + 1

s.close()
print(json.dumps({"packets": n, "pt_counts": pt_counts}, ensure_ascii=False))
