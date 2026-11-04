# -*- coding: utf-8 -*-
import ctypes
dll = ctypes.WinDLL(r"C:\Windows\System32\Npcap\wpcap.dll")
class pcap_if_t(ctypes.Structure): pass
pcap_if_t._fields_ = [("next", ctypes.POINTER(pcap_if_t)), ("name", ctypes.c_char_p),
                      ("description", ctypes.c_char_p), ("addresses", ctypes.c_void_p),
                      ("flags", ctypes.c_uint)]
alldevs = ctypes.POINTER(pcap_if_t)()
eb = ctypes.create_string_buffer(256)
dll.pcap_findalldevs(ctypes.byref(alldevs), eb)
devs = []
p = alldevs
while p:
    nm = p.contents.name.decode(errors='replace')
    ds = p.contents.description.decode(errors='replace') if p.contents.description else ""
    devs.append((nm, ds)); p = p.contents.next
dll.pcap_freealldevs(alldevs)

dll.pcap_open_live.restype = ctypes.c_void_p
dll.pcap_open_live.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
dll.pcap_sendpacket.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
dll.pcap_close.argtypes = [ctypes.c_void_p]
dll.pcap_geterr.restype = ctypes.c_char_p
dll.pcap_geterr.argtypes = [ctypes.c_void_p]

skip = ("WAN Miniport", "Bluetooth", "VMware", "Wi-Fi Direct", "Loopback", "Microsoft")
for nm, ds in devs:
    if any(s in ds for s in skip):
        continue
    e = ctypes.create_string_buffer(256)
    h = dll.pcap_open_live(nm.encode(), 65536, 0, 500, e)
    if not h:
        print("%-46s OPEN FAIL %s" % (ds[:46], e.value.decode(errors='replace')[:60])); continue
    fr = bytearray(60); fr[0:6] = b'\xff'*6; fr[6:12] = b'\x02\x00\x00\x00\x00\x01'
    fr[12:14] = b'\x88\xb5'; fr[14:18] = b'RTC2'
    rc = dll.pcap_sendpacket(h, bytes(fr), len(fr))
    err = "" if rc == 0 else dll.pcap_geterr(h).decode(errors='replace')[:70]
    print("%-46s send rc=%2d %s" % (ds[:46], rc, err))
    dll.pcap_close(h)
