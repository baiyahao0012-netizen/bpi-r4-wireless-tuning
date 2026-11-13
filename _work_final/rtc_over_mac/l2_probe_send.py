#!/usr/bin/env python3
"""Send a minimal custom-EtherType L2 frame from Pi wlan1 to the laptop."""
import socket
import struct
import sys
import time

IFACE = "wlan1"
SRC = bytes.fromhex("90de801c6a7a")   # Pi wlan1
DST = bytes.fromhex("40c2ba527095")   # laptop Ethernet
ETHERTYPE = 0x88B5
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 20
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETHERTYPE))
s.bind((IFACE, 0))
for i in range(COUNT):
    payload = b"RTC2PROBE" + struct.pack("!I", i) + b"\x00" * 16
    frame = DST + SRC + struct.pack("!H", ETHERTYPE) + payload
    s.send(frame)
    print("sent", i, len(frame), flush=True)
    time.sleep(INTERVAL)
s.close()
