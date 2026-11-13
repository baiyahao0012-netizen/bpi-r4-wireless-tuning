#!/usr/bin/env python3
"""Prototype: RTP from local GStreamer UDP -> 12-byte L2 shim on wlan1."""
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
udp.bind(("127.0.0.1", UDP_PORT))
udp.settimeout(1.0)
print("l2_rtp_send listening udp/%d on %s" % (UDP_PORT, IFACE), flush=True)

n = 0
last = time.time()
while True:
    try:
        data, _ = udp.recvfrom(65535)
    except socket.timeout:
        if n and time.time() - last > 5:
            break
        continue
    if len(data) > MTU:
        continue
    n += 1
    last = time.time()
    # ver/type=0x11, flags=0, flow, len, ttl, hdr_len, crc, stream
    hdr = struct.pack("!BBHHBBHH", 0x11, 0, FLOW, len(data), 8, 12, 0, 0)
    crc = binascii.crc_hqx(hdr + data, 0)
    hdr = struct.pack("!BBHHBBHH", 0x11, 0, FLOW, len(data), 8, 12, crc, 0)
    frame = DST + SRC + struct.pack("!H", ETHERTYPE) + hdr + data
    sock.send(frame)
    if n % 500 == 0:
        print("sent", n, flush=True)

print("total", n, flush=True)
