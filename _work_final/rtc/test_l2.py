# -*- coding: utf-8 -*-
import ctypes, os

PCAP_ERRBUF_SIZE = 256
dll = ctypes.WinDLL(r"C:\Windows\System32\Npcap\wpcap.dll")

class pcap_if_t(ctypes.Structure): pass
pcap_if_t._fields_ = [("next", ctypes.POINTER(pcap_if_t)), ("name", ctypes.c_char_p),
                      ("description", ctypes.c_char_p), ("addresses", ctypes.c_void_p),
                      ("flags", ctypes.c_uint)]

alldevs = ctypes.POINTER(pcap_if_t)()
errbuf = ctypes.create_string_buffer(PCAP_ERRBUF_SIZE)
if dll.pcap_findalldevs(ctypes.byref(alldevs), errbuf) != 0:
    print("findalldevs failed:", errbuf.value); raise SystemExit(1)

targets = []
p = alldevs
while p:
    nm = p.contents.name.decode(errors='replace')
    ds = p.contents.description.decode(errors='replace') if p.contents.description else ""
    if "Wi-Fi" in ds or "Wireless" in ds or "GbE" in ds:
        targets.append((nm, ds))
    p = p.contents.next
dll.pcap_freealldevs(alldevs)

dll.pcap_open_live.restype = ctypes.c_void_p
dll.pcap_open_live.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p]

for nm, ds in targets:
    eb = ctypes.create_string_buffer(PCAP_ERRBUF_SIZE)
    h = dll.pcap_open_live(nm.encode(), 65536, 0, 1000, eb)
    tag = ds[:45]
    if not h:
        print("[OPEN FAIL] %-45s %s" % (tag, eb.value.decode(errors='replace')))
        continue
    print("[OPEN OK  ] %-45s" % tag)

    # try send a 60-byte 0x88B5 frame to broadcast
    frame = bytearray(60)
    frame[0:6] = b'\xff' * 6
    frame[6:12] = b'\x02\x00\x00\x00\x00\x01'
    frame[12:14] = b'\x88\xb5'
    frame[14:18] = b'RTC2'
    dll.pcap_sendpacket.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    rc = dll.pcap_sendpacket(h, bytes(frame), len(frame))
    print("           send rc=%d %s" % (rc, "" if rc == 0 else "(nonzero = fail)"))
    dll.pcap_close.argtypes = [ctypes.c_void_p]
    dll.pcap_close(h)
