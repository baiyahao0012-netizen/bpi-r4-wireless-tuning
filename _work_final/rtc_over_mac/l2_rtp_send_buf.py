#!/usr/bin/env python3
"""Prototype: RTP from local GStreamer UDP -> 12-byte L2 shim on wlan1.

Fix vs l2_rtp_send.py: large SO_RCVBUF on the local UDP socket, and a
WARN log when the kernel drops datagrams (SO_RXQ_OVFL).
"""
import binascii
import socket
import struct
import sys
import time

IFACE = "wlan1"
SRC = bytes.fromhex("90de801c6a7a")
DST = bytes.fromhex("40c2ba527095")
ETHERTYPE = 0x88B5
FLOW = 1
UDP_PORT = 5004
MTU = 1400

sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE))
sock.bind((IFACE, 0))

udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
try:
    udp.setsockopt(socket.SOL_SOCKET, 49, 1)  # SO_RXQ_OVFL
except OSError:
    pass
udp.bind(("127.0.0.1", UDP_PORT))
udp.settimeout(1.0)
print("l2_rtp_send_buf listening udp/%d on %s rcvbuf=%d"
      % (UDP_PORT, IFACE, udp.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)), flush=True)

n = 0
dropped = 0
last = time.time()
while True:
    try:
        data, anc, flags, addr = udp.recvmsg(65535, 1024)
    except socket.timeout:
        if n and time.time() - last > 5:
            break
        continue
    for level, typ, cdata in anc:
        if level == socket.SOL_SOCKET and typ == 49 and len(cdata) >= 4:
            dropped = struct.unpack("I", cdata[:4])[0]
    if len(data) > MTU:
        continue
    n += 1
    last = time.time()
    hdr = struct.pack("!BBHHBBHH", 0x11, 0, FLOW, len(data), 8, 12, 0, 0)
    crc = binascii.crc_hqx(hdr + data, 0)
    hdr = struct.pack("!BBHHBBHH", 0x11, 0, FLOW, len(data), 8, 12, crc, 0)
    frame = DST + SRC + struct.pack("!H", ETHERTYPE) + hdr + data
    sock.send(frame)
    if n % 5000 == 0:
        print("sent", n, "kernel_drops", dropped, flush=True)

print("total", n, "kernel_drops", dropped, flush=True)
