#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast packet capture on Windows via Npcap pcap_next_ex (ctypes)."""
import ctypes as C
import os
import socket
import struct


class _timeval(C.Structure):
    _fields_ = [("tv_sec", C.c_long), ("tv_usec", C.c_long)]


class _pkthdr(C.Structure):
    _fields_ = [("ts", _timeval), ("caplen", C.c_uint32), ("len", C.c_uint32)]


class _bpf(C.Structure):
    _fields_ = [("bf_len", C.c_uint), ("bf_insns", C.c_void_p)]


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


class PcapRx:
    def __init__(self, ip, bpf=None, snaplen=65535):
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
        dll.pcap_open_live.argtypes = [C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_char_p]
        dll.pcap_open_live.restype = C.c_void_p
        dll.pcap_compile.argtypes = [C.c_void_p, C.POINTER(_bpf), C.c_char_p, C.c_int, C.c_uint32]
        dll.pcap_setfilter.argtypes = [C.c_void_p, C.POINTER(_bpf)]
        dll.pcap_next_ex.argtypes = [C.c_void_p, C.POINTER(C.POINTER(_pkthdr)),
                                     C.POINTER(C.POINTER(C.c_ubyte))]
        dll.pcap_geterr.argtypes = [C.c_void_p]
        dll.pcap_geterr.restype = C.c_char_p
        dev = self._find_by_ip(ip)
        if dev is None:
            raise OSError("no adapter with ip %s" % ip)
        errbuf = C.create_string_buffer(256)
        self.handle = dll.pcap_open_live(dev, snaplen, 0, 1, errbuf)
        if not self.handle:
            raise OSError("open: %s" % errbuf.value)
        if bpf:
            prog = _bpf()
            if dll.pcap_compile(self.handle, C.byref(prog), bpf.encode(), 1, 0xFFFFFFFF) != 0:
                raise OSError("compile %s: %s" % (bpf, dll.pcap_geterr(self.handle)))
            if dll.pcap_setfilter(self.handle, C.byref(prog)) != 0:
                raise OSError("setfilter: %s" % dll.pcap_geterr(self.handle))

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

    def next_packet(self):
        hdr = C.POINTER(_pkthdr)()
        data = C.POINTER(C.c_ubyte)()
        rc = self.dll.pcap_next_ex(self.handle, C.byref(hdr), C.byref(data))
        if rc == 1:
            return C.string_at(data, hdr.contents.caplen)
        if rc == 0:
            return None
        if rc < 0:
            raise OSError("pcap_next_ex rc=%d %s" % (rc, self.dll.pcap_geterr(self.handle)))
        return None
