#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01 最小 RTP 头演示（纯标准库，无任何 RTC 框架）
=================================================
目的：不看 GStreamer，先把 RTP 12 字节固定头亲手拼一遍、拆一遍，
      理解每个比特位对应什么字段。

演示流程（本机 127.0.0.1 自收自发，3 个数字）：
  A 端：手工拼 12 字节 RTP 头 + 1 字节载荷 -> UDP 发出
  B 端：UDP 收包 -> 拆 12 字节头 -> 取出载荷还原

运行：python 01_rtp_header_demo.py
对照 RFC 3550 第 5.1 节 RTP 头格式。
"""

import socket
import struct
import threading

HOST = "127.0.0.1"   # 本机回环，不经过真实网络，纯演示打包/拆包
PORT = 9999
SSRC = 0x11223344    # 32 位同步源标识；真实会议里由发送端随机生成，全会话不变
PT = 96              # 7 位动态载荷类型：这里借用 96 表示 H.264（Opus 用 111）


def build_rtp(payload, seq, ts, marker=1):
    """拼一个 RTP 包：12 字节固定头 + 载荷。

    struct 格式 "!BBHII" 逐段对应（! 表示网络字节序/大端）：
        !   大端字节序（RTP/网络协议统一大端）
        B   1 字节：version(2)|padding(1)|extension(1)|CC(4)
        B   1 字节：marker(1)|payload type(7)
        H   2 字节：sequence number（16 位无符号）
        I   4 字节：timestamp（32 位无符号）
        I   4 字节：SSRC（32 位无符号）
        合计 1+1+2+4+4 = 12 字节固定头
    """
    # 第 1 字节：V=2 占最高 2 位 -> 二进制 10 000000 = 0x80；P/X/CC 全 0
    b0 = 0x80

    # 第 2 字节：M 占最高 1 位，PT 占低 7 位。marker=1 表示这是一帧的最后一包
    b1 = (marker << 7) | PT

    # 按网络字节序打包头部
    header = struct.pack("!BBHII", b0, b1, seq, ts, SSRC)
    return header + payload


def parse_rtp(packet):
    """拆 RTP 包，返回 (字段字典, 载荷)。"""
    # 先解出前两个字节和三个整数字段
    b0, b1, seq, ts, ssrc = struct.unpack("!BBHII", packet[:12])

    fields = {
        "V":   (b0 >> 6) & 0x03,   # 最高 2 位：版本号，必须是 2
        "P":   (b0 >> 5) & 0x01,   # 第 5 位：是否有填充
        "X":   (b0 >> 4) & 0x01,   # 第 4 位：是否有扩展头
        "CC":  b0 & 0x0F,          # 低 4 位：CSRC 个数
        "M":   (b1 >> 7) & 0x01,   # 最高 1 位：marker 帧边界
        "PT":  b1 & 0x7F,          # 低 7 位：载荷类型
        "seq": seq,                # 16 位序号
        "ts":  ts,                 # 32 位时间戳
        "ssrc": ssrc,              # 32 位同步源标识
    }
    # 12 字节之后全是载荷；真实包若有 CSRC/扩展/填充，偏移要相应后移（见 03 号文件）
    return fields, packet[12:]


def hexdump(data):
    """把字节流打印成十六进制，便于对照头结构逐字节看。"""
    return " ".join(f"{b:02x}" for b in data)


def receiver(ready, results):
    """B 端：绑定 UDP 端口，收 3 个包后拆头，存进 results。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    sock.settimeout(5)
    ready.set()                      # 通知主线程：接收端已就绪，可以发了
    for _ in range(3):
        packet, addr = sock.recvfrom(2048)
        fields, payload = parse_rtp(packet)
        results.append((packet, fields, payload, addr))
    sock.close()


def main():
    ready = threading.Event()
    results = []

    # 起接收线程（UDP 收包是阻塞调用，放线程里）
    th = threading.Thread(target=receiver, args=(ready, results), daemon=True)
    th.start()
    ready.wait()

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 30 fps -> 90 kHz 时钟，每帧时间戳步长 = 90000/30 = 3000
    for i, digit in enumerate([b"1", b"2", b"3"]):
        seq = i + 1                  # 序号从 1 开始递增
        ts = i * 3000                # 时间戳按步长累加
        packet = build_rtp(digit, seq, ts)
        # sendto 交给内核；内核在外面套 UDP 头(8B) + IP 头(20B)，RTP 本身不碰这些
        sender.sendto(packet, (HOST, PORT))

        print(f"[A] payload={digit!r}  seq={seq}  ts={ts}")
        print(f"[A] 打包后 {len(packet)} 字节: {hexdump(packet)}")
        print(f"[A] sendto -> {HOST}:{PORT} (SOCK_DGRAM / UDP)")
        print()

    sender.close()
    th.join(timeout=5)

    for packet, fields, payload, addr in results:
        print(f"[B] 收到 {len(packet)} 字节 from {addr[0]}:{addr[1]}")
        print(f"[B] 拆头: {fields}")
        print(f"[B] 取出载荷: {payload!r}  -> 还原成数字 {payload.decode()}")
        print()

    print("=" * 60)
    print("内核全程只做了一件事：把这段字节塞进 UDP 包，加 8 字节 UDP 头")
    print("和 20 字节 IP 头，交给网卡。它不认识 RTP，也没碰过 RTP。")


if __name__ == "__main__":
    main()
