#!/usr/bin/env python3
"""Prototype: capture L2 shim on Windows Ethernet -> local RTP UDP for GStreamer."""
import binascii
import socket
import struct
import sys

from scapy.all import Ether, sniff, conf

conf.bufsize = 64 * 1024 * 1024
conf.sniff_promisc = False
conf.use_pcap = True

IFACE = r"\Device\NPF_{A2958734-FBD5-4E72-AD1C-362588589CD1}"
ETHERTYPE = 0x88B5
UDP_OUT = ("127.0.0.1", 5014)
out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
n = 0
bad = 0


def cb(pkt):
    global n, bad
    if Ether not in pkt or pkt[Ether].type != ETHERTYPE:
        return
    raw = bytes(pkt[Ether].payload)
    if len(raw) < 12:
        bad += 1
        return
    ver_type, flags, flow, plen, ttl, hlen, crc, stream = struct.unpack("!BBHHBBHH", raw[:12])
    if (ver_type >> 4) != 1 or hlen != 12 or len(raw) < hlen + plen:
        bad += 1
        return
    payload = raw[hlen:hlen + plen]
    hdr0 = bytearray(raw[:12])
    hdr0[8:10] = b"\x00\x00"
    if binascii.crc_hqx(bytes(hdr0) + payload, 0) != crc:
        bad += 1
        return
    out.sendto(payload, UDP_OUT)
    n += 1
    if n % 500 == 0:
        print("rx", n, "bad", bad, flush=True)


sniff(iface=IFACE, filter="ether proto 0x88b5", timeout=120, store=False, prn=cb)
print("total", n, "bad", bad, flush=True)
