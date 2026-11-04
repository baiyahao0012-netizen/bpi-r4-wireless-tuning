# -*- coding: utf-8 -*-
"""Validate: raw 0x88B5 sent on Ethernet reaches the Wi-Fi STA via board bridge."""
import ctypes, time, sys
import rtc2

dll = ctypes.WinDLL(r"C:\Windows\System32\Npcap\wpcap.dll")
class pcap_if_t(ctypes.Structure): pass
pcap_if_t._fields_ = [("next", ctypes.POINTER(pcap_if_t)), ("name", ctypes.c_char_p),
                      ("description", ctypes.c_char_p), ("addresses", ctypes.c_void_p),
                      ("flags", ctypes.c_uint)]
class timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]
class pcap_pkthdr(ctypes.Structure):
    _fields_ = [("ts", timeval), ("caplen", ctypes.c_uint), ("len", ctypes.c_uint)]

dll.pcap_open_live.restype = ctypes.c_void_p
dll.pcap_open_live.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_char_p]
dll.pcap_sendpacket.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
dll.pcap_close.argtypes=[ctypes.c_void_p]
dll.pcap_setdirection.argtypes=[ctypes.c_void_p,ctypes.c_int]
dll.pcap_geterr.restype=ctypes.c_char_p; dll.pcap_geterr.argtypes=[ctypes.c_void_p]
dll.pcap_next_ex.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.POINTER(pcap_pkthdr)),
                           ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]

def find(sub):
    alldevs=ctypes.POINTER(pcap_if_t)(); eb=ctypes.create_string_buffer(256)
    dll.pcap_findalldevs(ctypes.byref(alldevs), eb)
    out=[]; p=alldevs
    while p:
        ds=(p.contents.description or b"").decode(errors='replace')
        if sub in ds: out.append(p.contents.name.decode(errors='replace'))
        p=p.contents.next
    dll.pcap_freealldevs(alldevs)
    return out

ETH = find("GbE Family")[0]
WIFI = find("8852")[0]

def mac(s): return bytes.fromhex(s.replace('-','').replace(':',''))
SRC = mac("40-C2-BA-52-70-95")
DST = mac("C0-35-32-19-CC-FB")

def openh(dev, direction=None):
    e=ctypes.create_string_buffer(256)
    h=dll.pcap_open_live(dev.encode(), 65536, 0, 100, e)
    if not h: raise RuntimeError("open %s: %s" % (dev, e.value.decode(errors='replace')))
    if direction is not None: dll.pcap_setdirection(h, direction)
    return h

hrx = openh(WIFI, 1)     # PCAP_D_IN
htx = openh(ETH)

N = 20
payload = b"RTC2-PATH-TEST-" + b"x" * 100
frames, _ = rtc2.chunk_frame(payload, frame_id=1, pts=0, send_ts_us=0, seq_start=0)
body = frames[0]
wire = DST + SRC + b"\x88\xb5" + body

sent = 0
for i in range(N):
    rc = dll.pcap_sendpacket(htx, wire, len(wire))
    if rc == 0: sent += 1
    else: print("send fail:", dll.pcap_geterr(htx).decode(errors='replace')[:60])
    time.sleep(0.01)
print("sent %d/%d frames on Ethernet -> dst %s" % (sent, N, "C0:35:32:19:CC:FB"))

# drain
got = 0; t0 = time.time()
hdr=ctypes.POINTER(pcap_pkthdr)(); data=ctypes.POINTER(ctypes.c_ubyte)()
deadline = time.time() + 1.5
while time.time() < deadline:
    r = dll.pcap_next_ex(hrx, ctypes.byref(hdr), ctypes.byref(data))
    if r == 1:
        raw = bytes(bytearray(data[:hdr.contents.caplen]))
        if len(raw) >= 14 and raw[12:14] == b"\x88\xb5":
            got += 1
print("received %d 0x88B5 frames on Wi-Fi (direction=IN)" % got)
dll.pcap_close(hrx); dll.pcap_close(htx)
print("RESULT:", "PASS" if got > 0 else "FAIL")
