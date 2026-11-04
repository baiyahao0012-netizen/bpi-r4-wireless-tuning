# -*- coding: utf-8 -*-
import ctypes
dll = ctypes.WinDLL(r"C:\Windows\System32\Npcap\wpcap.dll")
class pcap_if_t(ctypes.Structure): pass
pcap_if_t._fields_ = [("next", ctypes.POINTER(pcap_if_t)), ("name", ctypes.c_char_p),
                      ("description", ctypes.c_char_p), ("addresses", ctypes.c_void_p),
                      ("flags", ctypes.c_uint)]
alldevs = ctypes.POINTER(pcap_if_t)(); eb = ctypes.create_string_buffer(256)
dll.pcap_findalldevs(ctypes.byref(alldevs), eb)
devs=[]; p=alldevs
while p:
    devs.append((p.contents.name.decode(errors='replace'),
                 (p.contents.description or b"").decode(errors='replace')))
    p=p.contents.next
dll.pcap_freealldevs(alldevs)
dll.pcap_can_set_rfmon.argtypes=[ctypes.c_void_p]
dll.pcap_open_live.restype=ctypes.c_void_p
dll.pcap_open_live.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_char_p]
dll.pcap_close.argtypes=[ctypes.c_void_p]
for nm, ds in devs:
    if "8852" in ds or "MediaTek" in ds:
        e=ctypes.create_string_buffer(256)
        h=dll.pcap_open_live(nm.encode(),65536,0,300,e)
        can = dll.pcap_can_set_rfmon(h) if h else -1
        print("%-46s rfmon_capable=%d" % (ds[:46], can))
        if h: dll.pcap_close(h)
print("Npcap version:", dll.pcap_lib_version.__call__() if hasattr(dll,'pcap_lib_version') else "?")
