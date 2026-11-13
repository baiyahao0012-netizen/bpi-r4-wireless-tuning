#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rtcp_sr_probe.py — RTCP SR（发送方报告）字段级解析探针（测量工具，不参与媒体收发）

RFC 3550 §6.4.1 SR 报文结构（单位：字节）：
  0   : V(2) P(1) RC(5)
  1   : PT = 200
  2-3 : length（32 位字数 - 1，大端）
  4-7 : sender SSRC（发送方标识）
  8-11: NTP 时间戳高 32 位（自 1900-01-01 起的秒数）
  12-15: NTP 时间戳低 32 位（秒的小数部分 / 2^32）
  16-19: RTP 时间戳（与 NTP 同一时刻，供接收端换算 A/V 时钟）
  20-23: 已发送 RTP 包数
  24-27: 已发送 RTP 载荷字节数
  28..: 接收方报告块（本自测只有单发送方，通常为空）

RTCP 允许一个 UDP 报文中捆绑多个报文（compound），因此按 length 字段逐个切片。

用法：python3 rtcp_sr_probe.py [端口] [监听秒数]
输出 JSON：包总数、PT 计数、SR 明细、一致性校验结论。
"""

import json
import socket
import struct
import sys
import time

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5035
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 16.0

# NTP 纪元（1900-01-01）与 Unix 纪元（1970-01-01）相差的秒数
NTP_EPOCH_OFFSET = 2208988800

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", port))
s.settimeout(0.5)

n = 0
pt_counts = {}
sr_list = []
end = time.time() + duration


def parse_sr(body, start):
    """解析一条 SR 报文的发送方信息；返回 dict 或 None（长度不足）。"""
    if len(body) < start + 28:
        return None
    ssrc, ntp_hi, ntp_lo, rtp_ts, pkt_cnt, oct_cnt = struct.unpack_from(
        ">IIIIII", body, start + 4
    )
    ntp_sec = ntp_hi - NTP_EPOCH_OFFSET + ntp_lo / 2 ** 32
    return {
        "ssrc": ssrc,
        "ntp_sec": round(ntp_sec, 6),
        "ntp_hi": ntp_hi,
        "ntp_lo": ntp_lo,
        "rtp_ts": rtp_ts,
        "packets": pkt_cnt,
        "octets": oct_cnt,
    }


while time.time() < end:
    try:
        data, _ = s.recvfrom(65535)
    except socket.timeout:
        continue
    # 复合包切片：offset 0 起，按 length 字段推进
    off = 0
    while off + 8 <= len(data):
        if data[off] >> 6 != 2:
            break
        pt = data[off + 1]
        length_words = struct.unpack_from(">H", data, off + 2)[0]
        pkt_size = (length_words + 1) * 4
        pkt = data[off:off + pkt_size]
        n += 1
        pt_counts[str(pt)] = pt_counts.get(str(pt), 0) + 1
        if pt == 200:  # SR
            sr = parse_sr(pkt, 0)
            if sr:
                sr_list.append(sr)
        off += pkt_size

s.close()

# ---- 一致性校验 ----
checks = {}
if sr_list:
    ssrs = {x["ssrc"] for x in sr_list}
    checks["single_sender_ssrc"] = len(ssrs) == 1
    # 包数/字节数应单调不减
    pkts = [x["packets"] for x in sr_list]
    octs = [x["octets"] for x in sr_list]
    checks["packets_monotonic"] = all(b >= a for a, b in zip(pkts, pkts[1:]))
    checks["octets_monotonic"] = all(b >= a for a, b in zip(octs, octs[1:]))
    # NTP 与 RTP 时间映射：RTP 时钟 90 kHz，RTP 增量/90000 应≈ NTP 增量
    if len(sr_list) >= 2:
        d_rtp = sr_list[-1]["rtp_ts"] - sr_list[0]["rtp_ts"]
        d_ntp = sr_list[-1]["ntp_sec"] - sr_list[0]["ntp_sec"]
        rtp_rate = d_rtp / d_ntp if d_ntp > 0 else None
        checks["ntp_rtp_rate_hz"] = round(rtp_rate, 1) if rtp_rate else None
        checks["ntp_rtp_rate_ok"] = bool(rtp_rate and 80000 <= rtp_rate <= 100000)
    else:
        checks["ntp_rtp_rate_ok"] = None
else:
    checks = {"single_sender_ssrc": False}

print(json.dumps({
    "packets": n,
    "pt_counts": pt_counts,
    "sr_count": len(sr_list),
    "sr_sample": sr_list[:3],
    "checks": checks,
}, ensure_ascii=False))
