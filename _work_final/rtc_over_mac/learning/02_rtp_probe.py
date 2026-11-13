#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02 RTP 探针（测量工具，不参与媒体收发）
==========================================
职责：在指定 UDP 端口收包，解析 RTP 固定头，统计：
  - 总包数、载荷字节数
  - 序号缺口（乱序/丢包的初步线索）
  - SSRC 集合（应该只有 1 个；多个说明有混流/串流）
  - 出现过多少个不同时间戳（≈ 帧数线索）
  - 首包/末包的 (seq, ts, ssrc, pt, 长度)

用法：python3 02_rtp_probe.py <端口> <秒数>
示例：python3 02_rtp_probe.py 5004 14

注意：
  - 这是应用层 UDP 收包，只用于本地回环/基线测量；
  - 序号缺口 ≠ 最终丢包率：乱序、抖动缓冲重排、A-MSDU 聚合都会影响，
    最终帧完整率要靠 03 号文件重建 H.264 后数帧得到。
"""

import json
import socket
import struct
import sys
import time

# 命令行参数：端口默认 5004，收包时长默认 12 秒
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5004
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0

# SOCK_DGRAM = UDP；SO_REUSEADDR 允许端口快速重启复用
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", port))
s.settimeout(0.5)   # 每次 recvfrom 最多等 0.5 秒，超时就回到循环判断是否到期

# 统计量初始化
n = 0                                   # 总包数
payload_bytes = 0                       # 载荷总字节（去掉 12B 头）
first = last = None                     # 首包/末包快照
ssrcs = set()                           # 出现过的所有 SSRC
pts = set()                             # 出现过的所有时间戳
seq_gaps = 0                            # 序号缺口计数
prev = None                             # 上一包序号
end = time.time() + duration            # 收包截止时刻

while time.time() < end:
    try:
        data, _ = s.recvfrom(65535)     # UDP 单包最大 65535 字节
    except socket.timeout:
        continue                         # 这一轮没包，继续等到截止时刻

    if len(data) < 12:                   # 不足 12 字节，不是合法 RTP，跳过
        continue

    # 第 1 字节高 2 位 = 版本号；RTP 必须是 2，不是就跳过
    v = data[0] >> 6
    if v != 2:
        continue

    # 第 2 字节低 7 位 = 载荷类型
    pt = data[1] & 0x7F
    # 字节 2–3：16 位序号（大端无符号）
    seq = struct.unpack("!H", data[2:4])[0]
    # 字节 4–7：32 位时间戳
    ts = struct.unpack("!I", data[4:8])[0]
    # 字节 8–11：32 位 SSRC
    ssrc = struct.unpack("!I", data[8:12])[0]

    # 序号缺口判定：相对上一包的差值（按 16 位回绕取模）。
    # 差值 0 = 重复包；1 = 连续；其他 = 缺口（可能丢包/乱序/聚合）。
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

# 结果输出为 JSON，便于脚本二次解析；ensure_ascii=False 保留中文可读性
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
