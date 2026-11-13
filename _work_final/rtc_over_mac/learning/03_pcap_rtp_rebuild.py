#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03 从 AP 侧 pcap 重建 H.264 并数解码帧（最硬核的一份）
=========================================================
输入：AP 无线口抓的 pcap（UDP 5004 上的 H.264 RTP）
输出：
  1) 统计：包数、序号首末、序号缺口、SSRC 分布、不同时间戳个数
  2) 重建出 Annex-B 格式的 .h264 文件（可拿回 Pi/PC 解码）
  3) 用 PyAV 实际解码，数出解码帧数

为什么需要这份文件：
  AP 抓到的是 RTP 包，不是视频文件。要回答"收到多少完整帧"，必须先按
  RFC 6184 把 RTP 载荷重新拼回 H.264 NAL 单元，再交给解码器数帧。

H.264 RTP 封装三种形态（RFC 6184）：
  - NAL 类型 1–23：单 NAL，一个 RTP 包装一个完整 NAL；
  - NAL 类型 24 ：STAP-A，一个包里聚合多个小 NAL，每个前面带 2 字节长度；
  - NAL 类型 28 ：FU-A，大 NAL 被切成多个分片，靠 S/E 位重组。

依赖：pip install scapy av
用法：python3 03_pcap_rtp_rebuild.py <pcap路径> <输出h264路径>
"""

import struct
import sys
from collections import Counter

from scapy.all import PcapReader, UDP

# 默认路径可被命令行参数覆盖
PCAP = sys.argv[1] if len(sys.argv) > 1 else "ap_rtp.pcap"
OUT = sys.argv[2] if len(sys.argv) > 2 else "ap_rx.h264"


def rtp_payload(raw):
    """从一段 UDP 载荷里剥掉 RTP 头，返回 (载荷, PT, seq, ts, ssrc)。

    这里比 02 号探针多处理 CSRC / 扩展头 / 填充三种情况，偏移要往后挪。
    返回 None 表示不是合法 RTP。
    """
    if len(raw) < 12:
        return None

    b0, b1 = raw[0], raw[1]
    if b0 >> 6 != 2:                       # 版本号必须为 2
        return None

    cc = b0 & 0x0F                        # CSRC 个数（每个 4 字节）
    ext = (b0 >> 4) & 1                   # 是否有扩展头
    pad = (b0 >> 5) & 1                   # 是否有填充

    off = 12 + 4 * cc                     # 固定头 12B + CSRC 区
    if ext:
        # 扩展头：2B 长度字段（单位是 32 位字），后面跟 ext_len*4 字节
        if len(raw) < off + 4:
            return None
        ext_len = struct.unpack("!H", raw[off + 2:off + 4])[0]
        off += 4 + 4 * ext_len

    # 填充：最后 1 字节记录填充字节数，载荷结束位置要往前减
    end = len(raw) - (raw[-1] if pad and raw else 0)
    if off > end:
        return None

    payload = raw[off:end]
    pt = b1 & 0x7F
    seq = struct.unpack("!H", raw[2:4])[0]
    ts = struct.unpack("!I", raw[4:8])[0]
    ssrc = struct.unpack("!I", raw[8:12])[0]
    return payload, pt, seq, ts, ssrc


def main():
    out = bytearray()      # 重建出的 Annex-B 字节流
    n = 0                  # 合法 RTP 包数
    seqs = []              # 序号序列（用于算缺口）
    ssrcs = Counter()      # 每个 SSRC 收到多少包
    pts = Counter()        # 每个时间戳出现几次（同一帧多包）
    fu = None              # FU-A 重组缓冲区（跨包累积）

    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if UDP not in pkt:
                continue
            u = pkt[UDP]
            if u.dport != 5004:        # 只取视频 RTP 端口
                continue

            r = rtp_payload(bytes(u.payload))
            if not r:
                continue
            payload, pt, seq, ts, ssrc = r

            n += 1
            seqs.append(seq)
            ssrcs[ssrc] += 1
            pts[ts] += 1

            if not payload:
                continue

            # NAL 类型 = 载荷首字节低 5 位
            nal = payload[0] & 0x1F

            if 1 <= nal <= 23:
                # 单 NAL：加 Annex-B 起始码 00 00 00 01 后直接拼接
                out += b"\x00\x00\x00\x01" + payload

            elif nal == 24:  # STAP-A 聚合包
                i = 1
                while i + 2 <= len(payload):
                    # 每个子 NAL 前 2 字节是大端长度
                    sz = struct.unpack("!H", payload[i:i + 2])[0]
                    i += 2
                    if sz <= 0 or i + sz > len(payload):
                        break
                    out += b"\x00\x00\x00\x01" + payload[i:i + sz]
                    i += sz

            elif nal == 28:  # FU-A 分片
                if len(payload) < 2:
                    continue
                fu_ind = payload[0]     # FU indicator：高 3 位是禁止/优先级/类型占位
                fu_hdr = payload[1]     # FU header：S/E/R 位 + NAL 类型
                start = (fu_hdr >> 7) & 1   # S=1：分片第一片
                end = (fu_hdr >> 6) & 1     # E=1：分片最后一片
                typ = fu_hdr & 0x1F         # 原始 NAL 类型藏在 FU header 低 5 位

                if start:
                    # 第一片：用 indicator 高 3 位 + 原始类型，重建 NAL 首字节
                    fu = bytearray([(fu_ind & 0xE0) | typ])
                if fu is not None:
                    fu += payload[2:]        # 累积分片载荷（跳过 2B FU 头）
                    if end:
                        # 最后一片：整组 NAL 拼完，加起始码写入输出
                        out += b"\x00\x00\x00\x01" + bytes(fu)
                        fu = None

    # 写出重建的 H.264 文件
    open(OUT, "wb").write(out)

    # 序号缺口统计（16 位回绕取模）
    gaps = sum(
        1 for a, b in zip(seqs, seqs[1:])
        if ((b - a) & 0xFFFF) not in (0, 1)
    )

    print("packets", n)
    print("seq_first", seqs[0] if seqs else None, "seq_last", seqs[-1] if seqs else None)
    print("seq_gaps", gaps)
    print("ssrc", ssrcs.most_common(3))
    print("unique_timestamps", len(pts))
    print("h264_bytes", len(out), "->", OUT)

    # 用 PyAV 实际解码数帧；解码器不可用时降级为只输出文件，不报错退出
    try:
        import av
        ctx = av.CodecContext.create("h264", "r")
        frames = 0
        with av.open(OUT) as container:
            for frame in container.decode(video=0):
                frames += 1
        print("decoded_frames", frames)
    except Exception as e:
        print("decode_error", repr(e))


if __name__ == "__main__":
    main()
