#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_rtp_probe.py — 最小 RTP 头探针（测量工具，不参与媒体收发）

作用：
  监听一个 UDP 端口，把收到的每个包按 RTP 规范拆开 12 字节固定头，
  统计包数、载荷字节数、序号缺口、SSRC 集合、时间戳个数，最后输出一段 JSON。

它是"计量器"：只读数、不打包、不解码、不参与任何媒体路径。
被测的媒体层是 GStreamer 的 rtph264pay / rtpopuspay，不是本脚本。

RTP 固定头 12 字节（RFC 3550）：

  字节偏移  长度  字段
  0         1     高 2 位 V(版本=2) | 1 位 P | 1 位 X | 4 位 CC
  1         1     最高位 M(marker) | 低 7 位 PT(载荷类型)
  2-3       2     sequence number（序号，每包 +1，16 位回绕）
  4-7       4     timestamp（时间戳；视频 90 kHz 时钟）
  8-11      4     SSRC（同步源标识）

用法：
  python3 rtp_probe.py [端口] [监听秒数]
  例：python3 rtp_probe.py 5004 14
"""

import json
import socket
import struct
import sys
import time

# 命令行参数：端口默认 5004，监听时长默认 12 秒
port = int(sys.argv[1]) if len(sys.argv) > 1 else 5004
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0

# -----------------------------------------------------------------------------
# 建 UDP socket，绑定本机回环端口
#   SOCK_DGRAM  = UDP；SO_REUSEADDR = 端口被占时允许快速重启
#   0.5 秒超时：收不到包就循环继续，避免阻塞到死
# -----------------------------------------------------------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", port))
s.settimeout(0.5)

# 统计变量
n = 0                       # 收到的 RTP 包总数
payload_bytes = 0           # 去掉 12 字节头后的载荷字节数
first = None                # 第一个包：(seq, ts, ssrc, pt, len)
last = None                 # 最后一个包：同上
ssrcs = set()               # 出现过的 SSRC 集合（正常应只有 1 个）
pts = set()                 # 不同 RTP 时间戳个数（≈帧数）
seq_gaps = 0                # 序号缺口次数
prev = None                 # 上一个包的序号，用于算相邻差

end = time.time() + duration

while time.time() < end:
    try:
        data, _ = s.recvfrom(65535)
    except socket.timeout:
        continue

    # 不足 12 字节不可能是合法 RTP 头，跳过
    if len(data) < 12:
        continue

    # 字节 0 高 2 位 = 版本号；RTP 版本必须是 2，不是 2 就跳过
    v = data[0] >> 6
    if v != 2:
        continue

    # 字节 1 低 7 位 = PT（载荷类型）：视频 96，音频 111
    pt = data[1] & 0x7F
    # 字节 2-3：序号，大端无符号 16 位
    seq = struct.unpack("!H", data[2:4])[0]
    # 字节 4-7：时间戳，大端无符号 32 位
    ts = struct.unpack("!I", data[4:8])[0]
    # 字节 8-11：SSRC，大端无符号 32 位
    ssrc = struct.unpack("!I", data[8:12])[0]

    # 序号缺口检测：
    # 相邻包序号差应为 1（或 0，重复包）；用 16 位回绕算术 (seq - prev) & 0xFFFF。
    # 差不在 {0,1} 内 = 丢包或乱序，记一次缺口。
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

# -----------------------------------------------------------------------------
# 输出 JSON 统计。判读要点：
#   ssrcs 多于 1 个        → 有混流/串流
#   seq_gaps > 0           → 有丢包或乱序（本地回环应为 0）
#   timestamps ≈ 帧数      → 30 fps × 10 s ≈ 300 个时间戳
#   first/last 的 pt       → 与发送侧 rtppay 参数一致
# -----------------------------------------------------------------------------
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
