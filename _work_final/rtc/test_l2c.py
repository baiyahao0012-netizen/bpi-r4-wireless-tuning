# -*- coding: utf-8 -*-
import ctypes, time
dll = ctypes.WinDLL(r"C:\Windows\System32\Npcap\wpcap.dll")
class pcap_if_t(ctypes.Structure): pass
pcap_if_t._fields_ = [("next", ctypes.POINTER(pcap_if_t)), ("name", ctypes.c_char_p),
                      ("description", ctypes.c_char_p), ("addresses", ctypes.c_void_p),
                      ("flags", ctypes.c_uint)]
class timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]
class pcap_pkthdr(ctypes.Structure):
    _fields_ = [("ts", timeval), ("caplen", ctypes.c_uint), ("len", ctypes.c_uint)]

alldevs = ctypes.POINTER(pcap_if_t)(); eb = ctypes.create_string_buffer(256)
dll.pcap_findalldevs(ctypes.byref(alldevs), eb)
devs=[]; p=alldevs
while p:
    devs.append((p.contents.name.decode(errors='replace'),
                 (p.contents.description or b"").decode(errors='replace')))
    p = p.contents.next
dll.pcap_freealldevs(alldevs)

dll.pcap_open_live.restype = ctypes.c_void_p
dll.pcap_open_live.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_char_p]
dll.pcap_sendpacket.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
dll.pcap_close.argtypes=[ctypes.c_void_p]
dll.pcap_geterr.restype=ctypes.c_char_p; dll.pcap_geterr.argtypes=[ctypes.c_void_p]
dll.pcap_next_ex.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.POINTER(pcap_pkthdr)),
                           ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]

wifi = [d for d in devs if "8852" in d[1]][0]
print("adapter:", wifi[1])

def mkframe(et):
    fr = bytearray(60); fr[0:6]=b'\xff'*6; fr[6:12]=b'\x02\x00\x00\x00\x00\x01'
    fr[12:14]=bytes.fromhex(et); return bytes(fr)

for et, name in (("88b5","custom 0x88B5"), ("0800","IPv4 0x0800"), ("0806","ARP 0x0806")):
    e=ctypes.create_string_buffer(256)
    h=dll.pcap_open_live(wifi[0].encode(),65536,0,500,e)
    rc=dll.pcap_sendpacket(h,mkframe(et),60)
    err = "" if rc==0 else dll.pcap_geterr(h).decode(errors='replace')[:60]
    print("  send %-16s rc=%2d %s" % (name, rc, err))
    dll.pcap_close(h)

# capture test
e=ctypes.create_string_buffer(256)
h=dll.pcap_open_live(wifi[0].encode(),65536,0,200,e)
if not h:
    print("capture open fail:", e.value.decode(errors='replace'))
else:
    hdr=ctypes.POINTER(pcap_pkthdr)(); data=ctypes.POINTER(ctypes.c_ubyte)()
    cnt=0; ets={}; t0=time.time()
    while time.time()-t0 < 2.0:
        r=dll.pcap_next_ex(h,ctypes.byref(hdr),ctypes.byref(data))
        if r==1:
            cnt+=1
            raw=bytes(bytearray(data[:hdr.contents.caplen]))
            if len(raw)>=14:
                et=raw[12:14].hex(); ets[et]=ets.get(et,0)+1
    print("capture 2s: %d frames, ethertypes=%s" % (cnt, dict(sorted(ets.items(), key=lambda x:-x[1])[:6])))
    dll.pcap_close(h)
