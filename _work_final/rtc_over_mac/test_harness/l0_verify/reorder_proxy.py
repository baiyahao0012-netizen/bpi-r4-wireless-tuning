#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reorder_proxy.py — RTP 乱序注入代理（测量工具，不参与媒体收发）

工作方式：
  监听 listen_port，把收到的 RTP 包转发到 dest_host:dest_port。
  按“成对交换”制造乱序：每收满 2 个包，按 [第2个, 第1个] 的顺序发出；
  不丢包、不改载荷，只打乱到达顺序，用于验证接收端 jitterbuffer 的重排能力。

RTP 序号在包头第 2-3 字节（大端 16 位），用于统计乱序程度。

用法：python3 reorder_proxy.py <listen_port> <dest_host> <dest_port> <运行秒数>
结束时输出 JSON：收包数、转发数、发出序列中的逆序对数量。
"""

import json
import socket
import struct
import sys
import time

listen_port = int(sys.argv[1])
dest_host = sys.argv[2]
dest_port = int(sys.argv[3])
duration = float(sys.argv[4])

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
recv_sock.bind(("127.0.0.1", listen_port))
recv_sock.settimeout(0.5)
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

received = 0
forwarded = 0
emitted_seq = []
buffer = []  # 成对缓存

end = time.time() + duration
while time.time() < end:
    try:
        data, _ = recv_sock.recvfrom(65535)
    except socket.timeout:
        # 超时把缓存里残留的包冲出去
        if buffer:
            for pkt in buffer:
                send_sock.sendto(pkt, (dest_host, dest_port))
                forwarded += 1
                emitted_seq.append(struct.unpack_from(">H", pkt, 2)[0])
            buffer = []
        continue
    received += 1
    buffer.append(data)
    if len(buffer) == 2:
        # 成对交换：先发后到的，再发先到的
        for pkt in (buffer[1], buffer[0]):
            send_sock.sendto(pkt, (dest_host, dest_port))
            forwarded += 1
            emitted_seq.append(struct.unpack_from(">H", pkt, 2)[0])
        buffer = []

if buffer:
    for pkt in buffer:
        send_sock.sendto(pkt, (dest_host, dest_port))
        forwarded += 1
        emitted_seq.append(struct.unpack_from(">H", pkt, 2)[0])

# 统计逆序对（发出序列里后包序号小于前包序号的次数）
inversions = sum(1 for i in range(1, len(emitted_seq)) if emitted_seq[i] < emitted_seq[i - 1])

recv_sock.close()
send_sock.close()
print(json.dumps({
    "received": received,
    "forwarded": forwarded,
    "inversions": inversions,
}, ensure_ascii=False))
