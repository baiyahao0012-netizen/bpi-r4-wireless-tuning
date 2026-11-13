#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
loss_proxy.py — RTP 丢包注入代理（测量工具，不参与媒体收发）

监听 listen_port，按确定性规则丢弃一部分 RTP 包后转发到 dest_host:dest_port。
规则：按序号取模，每 mod 个包丢 drop 个头部包（可复现，不用随机数）。
只丢 RTP 载荷包，不改包头；用于验证 NACK/RTX/PLI 恢复机制。

用法：python3 loss_proxy.py <listen_port> <dest_host> <dest_port> <mod> <drop> <运行秒数>
结束输出 JSON：收包、转发、丢弃数量与丢弃序号样本。
"""

import json
import socket
import struct
import sys
import time

listen_port = int(sys.argv[1])
dest_host = sys.argv[2]
dest_port = int(sys.argv[3])
mod = int(sys.argv[4])
drop = int(sys.argv[5])
duration = float(sys.argv[6])

recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
recv_sock.bind(("127.0.0.1", listen_port))
recv_sock.settimeout(0.5)
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

received = forwarded = dropped = 0
dropped_seq = []
end = time.time() + duration

while time.time() < end:
    try:
        data, _ = recv_sock.recvfrom(65535)
    except socket.timeout:
        continue
    received += 1
    seq = struct.unpack_from(">H", data, 2)[0]
    bucket = seq % mod
    if bucket < drop:
        dropped += 1
        if len(dropped_seq) < 20:
            dropped_seq.append(seq)
        continue
    send_sock.sendto(data, (dest_host, dest_port))
    forwarded += 1

recv_sock.close()
send_sock.close()
print(json.dumps({
    "received": received,
    "forwarded": forwarded,
    "dropped": dropped,
    "drop_ratio": round(dropped / received, 4) if received else 0,
    "dropped_seq_sample": dropped_seq,
}, ensure_ascii=False))
