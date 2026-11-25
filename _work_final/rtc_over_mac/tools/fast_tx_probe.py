#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe Npcap pcap_sendpacket throughput (fast path candidate for the server).

scapy's sendp costs ~12 ms/frame on Windows. This measures raw pcap_sendpacket
via ctypes; if it reaches several thousand pps, the server can use it instead.
"""
import ctypes as C
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import ETH_BULK, build_frame, mac_bytes

for cand in [r"C:\Windows\System32\Npcap\wpcap.dll", r"C:\Windows\System32\wpcap.dll"]:
    if os.path.exists(cand):
        wpcap = C.WinDLL(cand)
        break
else:
    raise SystemExit("wpcap.dll not found")


class sockaddr_in(C.Structure):
    _fields_ = [("family", C.c_ushort), ("port", C.c_ushort),
                ("addr", C.c_uint32), ("zero", C.c_ubyte * 8)]


class pcap_addr(C.Structure):
    pass


pcap_addr._fields_ = [("next", C.POINTER(pcap_addr)),
                      ("addr", C.POINTER(sockaddr_in)),
                      ("netmask", C.POINTER(sockaddr_in)),
                      ("broadaddr", C.POINTER(sockaddr_in)),
                      ("dstaddr", C.POINTER(sockaddr_in))]


class pcap_if(C.Structure):
    pass


pcap_if._fields_ = [("next", C.POINTER(pcap_if)),
                    ("name", C.c_char_p),
                    ("description", C.c_char_p),
                    ("addresses", C.POINTER(pcap_addr)),
                    ("flags", C.c_uint)]


wpcap.pcap_findalldevs.argtypes = [C.POINTER(C.POINTER(pcap_if)), C.c_char_p]
wpcap.pcap_findalldevs.restype = C.c_int
wpcap.pcap_open_live.argtypes = [C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_char_p]
wpcap.pcap_open_live.restype = C.c_void_p
wpcap.pcap_sendpacket.argtypes = [C.c_void_p, C.c_void_p, C.c_int]
wpcap.pcap_sendpacket.restype = C.c_int
wpcap.pcap_geterr.argtypes = [C.c_void_p]
wpcap.pcap_geterr.restype = C.c_char_p


def find_by_ip(want):
    alldevs = C.POINTER(pcap_if)()
    errbuf = C.create_string_buffer(256)
    if wpcap.pcap_findalldevs(C.byref(alldevs), errbuf) != 0:
        raise SystemExit("findalldevs: %s" % errbuf.value)
    dev = alldevs
    while dev:
        d = dev.contents
        a = d.addresses
        while a:
            sa = a.contents.addr
            if sa:
                sin = C.cast(sa, C.POINTER(sockaddr_in)).contents
                if sin.family == socket.AF_INET:
                    ip = socket.inet_ntoa(struct.pack("<I", sin.addr))
                    if ip == want:
                        return d.name
            a = a.contents.next
        dev = d.next
    return None


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.240.2"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    name = find_by_ip(ip)
    if not name:
        raise SystemExit("no adapter with ip %s" % ip)
    print("adapter:", name.decode(errors="replace"))
    errbuf = C.create_string_buffer(256)
    p = wpcap.pcap_open_live(name, 65535, 0, 1, errbuf)
    if not p:
        raise SystemExit("open: %s" % errbuf.value)
    frame = build_frame(mac_bytes("40:c2:ba:52:70:95"),
                        mac_bytes("90:de:80:1c:6a:7a"),
                        ETH_BULK, 1, 0, 2, 0, b"\x00" * 1354)
    buf = C.create_string_buffer(frame, len(frame))
    t0 = time.monotonic()
    sent = 0
    err = 0
    for _ in range(n):
        if wpcap.pcap_sendpacket(p, buf, len(frame)) == 0:
            sent += 1
        else:
            err += 1
            if err == 1:
                print("first error:", wpcap.pcap_geterr(p))
    dt = time.monotonic() - t0
    print("sent=%d err=%d time=%.3fs -> %.1f Mbps, %.0f pps" %
          (sent, err, dt, sent * len(frame) * 8 / dt / 1e6, sent / dt))


if __name__ == "__main__":
    main()
