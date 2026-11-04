# -*- coding: utf-8 -*-
import ctypes, time, collections
import l2sock

class pcap_stat(ctypes.Structure):
    _fields_ = [("ps_recv", ctypes.c_uint), ("ps_drop", ctypes.c_uint),
                ("ps_ifdrop", ctypes.c_uint)]

dll = l2sock._dll
dll.pcap_stats.argtypes = [ctypes.c_void_p, ctypes.POINTER(pcap_stat)]
dll.pcap_setbuff.argtypes = [ctypes.c_void_p, ctypes.c_int]

sock = l2sock.L2Socket(dev_substr="8852", direction=l2sock.PCAP_D_IN)
rc = dll.pcap_setbuff(sock._h, 16 * 1024 * 1024)
print("setbuff(16MB) rc=%d" % rc)

et = collections.Counter()
t0 = time.time()
last = t0
while time.time() - t0 < 12:
    r = sock.recv(0.02)
    if r is not None and len(r[1]) >= 14:
        et[r[1][12:14].hex()] += 1
    if time.time() - last >= 2.0:
        st = pcap_stat()
        dll.pcap_stats(sock._h, ctypes.byref(st))
        print("  t=%.0fs recv=%d drop=%d ifdrop=%d  0x88b5=%d 0x0800=%d"
              % (time.time() - t0, st.ps_recv, st.ps_drop, st.ps_ifdrop,
                 et.get('88b5', 0), et.get('0800', 0)))
        last = time.time()

st = pcap_stat()
dll.pcap_stats(sock._h, ctypes.byref(st))
print("FINAL recv=%d drop=%d ifdrop=%d" % (st.ps_recv, st.ps_drop, st.ps_ifdrop))
print("histogram:", dict(et.most_common(6)))
sock.close()
