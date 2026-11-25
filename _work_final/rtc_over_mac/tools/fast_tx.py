#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast L2 transmit on Windows via Npcap's pcap_sendpacket (ctypes).

scapy's sendp costs ~12 ms/frame (~10 Mbps of 1400 B frames), which makes the
server's application queue the permanent bottleneck and prevents the
"no-backlog" control (S6). pcap_sendpacket measured ~300k pps here.

Select the adapter by IPv4 address; falls back to scapy if Npcap is missing.
"""
import ctypes as C
import os
import socket
import struct


class _sockaddr_in(C.Structure):
    _fields_ = [("family", C.c_ushort), ("port", C.c_ushort),
                ("addr", C.c_uint32), ("zero", C.c_ubyte * 8)]


class _pcap_addr(C.Structure):
    pass


_pcap_addr._fields_ = [("next", C.POINTER(_pcap_addr)),
                       ("addr", C.POINTER(_sockaddr_in)),
                       ("netmask", C.POINTER(_sockaddr_in)),
                       ("broadaddr", C.POINTER(_sockaddr_in)),
                       ("dstaddr", C.POINTER(_sockaddr_in))]


class _pcap_if(C.Structure):
    pass


_pcap_if._fields_ = [("next", C.POINTER(_pcap_if)),
                     ("name", C.c_char_p),
                     ("description", C.c_char_p),
                     ("addresses", C.POINTER(_pcap_addr)),
                     ("flags", C.c_uint)]


class PcapTx:
    def __init__(self, ip):
        dll = None
        for cand in (r"C:\Windows\System32\Npcap\wpcap.dll",
                     r"C:\Windows\System32\wpcap.dll"):
            if os.path.exists(cand):
                dll = C.WinDLL(cand)
                break
        if dll is None:
            raise OSError("wpcap.dll not found")
        self.dll = dll
        dll.pcap_findalldevs.argtypes = [C.POINTER(C.POINTER(_pcap_if)), C.c_char_p]
        dll.pcap_findalldevs.restype = C.c_int
        dll.pcap_open_live.argtypes = [C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_char_p]
        dll.pcap_open_live.restype = C.c_void_p
        dll.pcap_sendpacket.argtypes = [C.c_void_p, C.c_void_p, C.c_int]
        dll.pcap_sendpacket.restype = C.c_int
        dll.pcap_geterr.argtypes = [C.c_void_p]
        dll.pcap_geterr.restype = C.c_char_p
        dev = self._find_by_ip(ip)
        if dev is None:
            raise OSError("no adapter with ip %s" % ip)
        errbuf = C.create_string_buffer(256)
        self.handle = dll.pcap_open_live(dev, 65535, 0, 1, errbuf)
        if not self.handle:
            raise OSError("open %s: %s" % (dev, errbuf.value))
        self.frames = 0
        self.errors = 0

    def _find_by_ip(self, want):
        alldevs = C.POINTER(_pcap_if)()
        errbuf = C.create_string_buffer(256)
        if self.dll.pcap_findalldevs(C.byref(alldevs), errbuf) != 0:
            return None
        dev = alldevs
        while dev:
            d = dev.contents
            a = d.addresses
            while a:
                sa = a.contents.addr
                if sa:
                    sin = C.cast(sa, C.POINTER(_sockaddr_in)).contents
                    if sin.family == socket.AF_INET:
                        ip = socket.inet_ntoa(struct.pack("<I", sin.addr))
                        if ip == want:
                            return d.name
                a = a.contents.next
            dev = d.next
        return None

    def send(self, frame):
        buf = C.create_string_buffer(frame, len(frame))
        rc = self.dll.pcap_sendpacket(self.handle, buf, len(frame))
        if rc == 0:
            self.frames += 1
        else:
            self.errors += 1
        return rc


class ScapyTx:
    def __init__(self, iface):
        from scapy.all import sendp, Ether, Raw
        self._sendp = sendp
        self._Ether = Ether
        self._Raw = Raw
        self.iface = iface
        self.frames = 0
        self.errors = 0

    def send(self, frame):
        try:
            self._sendp(self._Ether(frame[:14]) / self._Raw(frame[14:]),
                        iface=self.iface, verbose=0)
            self.frames += 1
            return 0
        except Exception:
            self.errors += 1
            return -1
