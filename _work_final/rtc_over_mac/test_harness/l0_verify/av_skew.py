#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
av_skew.py — 音画同步偏差分析（测量工具，不参与媒体收发）

输入：
  - 视频：原始 I420/YUV420p 文件（filesink 落盘，按解码顺序逐帧排列，无时间戳）
  - 音频：原始 S16LE PCM（单声道，采样率 rate）
  因为落盘文件不带 PTS，按“帧序号/帧率”“样本序号/采样率”还原时间轴。

锚点素材规则（见 make_anchor_material.py）：
  - 每 1 s 一整帧纯白（视频锚点）；TV range 白 Y≈235，阈值 >200 判白
  - 每 1 s 一段 50 ms、1 kHz 短音（音频锚点）；RMS > 1500 判为起音

输出 JSON：白帧数、短音段数、逐对偏差（音频起音时刻 - 白帧时刻，ms）、
          p50/p95/最大偏差、对齐结论。
"""

import json
import math
import struct
import sys

import argparse

p = argparse.ArgumentParser()
p.add_argument("--yuv", required=True)
p.add_argument("-W", type=int, required=True)
p.add_argument("-H", type=int, required=True)
p.add_argument("--fps", type=float, required=True)
p.add_argument("--pcm", required=True)
p.add_argument("--rate", type=int, required=True)
p.add_argument("--white", type=float, default=200.0)
p.add_argument("--rms", type=float, default=1500.0)
p.add_argument("--win-ms", type=float, default=20.0)
args = p.parse_args()

# ---------- 视频：逐帧平均亮度，找白帧时刻 ----------
frame_bytes = args.W * args.H * 3 // 2
flash_times = []
with open(args.yuv, "rb") as f:
    idx = 0
    while True:
        buf = f.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        y = buf[:args.W * args.H]
        mean = sum(y) / len(y)
        if mean > args.white:
            flash_times.append(idx / args.fps)
        idx += 1

# ---------- 音频：20 ms 窗 RMS，找短音起音时刻 ----------
raw = open(args.pcm, "rb").read()
samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
win = int(args.rate * args.win_ms / 1000)
onset_times = []
in_burst = False
for i in range(0, len(samples), win):
    seg = samples[i:i + win]
    rms = math.sqrt(sum(x * x for x in seg) / len(seg)) if seg else 0
    if rms > args.rms and not in_burst:
        in_burst = True
        onset_times.append(i / args.rate)
    elif rms <= args.rms:
        in_burst = False

# ---------- 按顺序配对，算偏差 ----------
pairs = min(len(flash_times), len(onset_times))
skew_ms = []
for k in range(pairs):
    skew_ms.append(round((onset_times[k] - flash_times[k]) * 1000.0, 2))

def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    pos = int(round((len(xs) - 1) * q))
    return xs[pos]

result = {
    "flash_frames": len(flash_times),
    "tone_bursts": len(onset_times),
    "pairs": pairs,
    "flash_times": [round(t, 3) for t in flash_times],
    "tone_times": [round(t, 3) for t in onset_times],
    "skew_ms": skew_ms,
    "skew_p50_ms": pct(skew_ms, 0.50),
    "skew_p95_ms": pct(skew_ms, 0.95),
    "skew_max_ms": max(skew_ms) if skew_ms else None,
}
# 对齐结论：配对数相等，且每对偏差绝对值 ≤ 40 ms（RTC 常用 A/V sync 门限）
result["aligned"] = (
    len(flash_times) == len(onset_times) == pairs
    and all(abs(x) <= 40.0 for x in skew_ms)
)
print(json.dumps(result, ensure_ascii=False))
