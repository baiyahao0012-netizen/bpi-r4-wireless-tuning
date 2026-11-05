# -*- coding: utf-8 -*-
"""Raw L2 socket over Npcap (Windows). Send + receive with direction filter."""
import ctypes, os, time

PCAP_D_IN = 1
PCAP_D_OUT = 0
PCAP_D_INOUT = 2

# Npcap installs its userland DLLs either into a Npcap subfolder (default
# since 0.99) or straight into System32 (WinPcap-compatible layout / OEM).
_CANDIDATES = [
    r"C:\Windows\System32\Npcap\wpcap.dll",
    r"C:\Windows\System32\wpcap.dll",
    r"C:\Windows\SysWOW64\Npcap\wpcap.dll",
    r"C:\Windows\SysWOW64\wpcap.dll",
]
_dll = None
for _p in _CANDIDATES:
    if os.path.exists(_p):
        try:
            _dll = ctypes.WinDLL(_p)
            break
        except OSError:
            continue
if _dll is None:
    raise OSError("wpcap.dll not found. Install Npcap (npcap.com) and retry.")


class _pcap_if_t(ctypes.Structure):
    pass
_pcap_if_t._fields_ = [("next", ctypes.POINTER(_pcap_if_t)),
                       ("name", ctypes.c_char_p),
                       ("description", ctypes.c_char_p),
                       ("addresses", ctypes.c_void_p),
                       ("flags", ctypes.c_uint)]

class _timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]

class _pkthdr(ctypes.Structure):
    _fields_ = [("ts", _timeval), ("caplen", ctypes.c_uint), ("len", ctypes.c_uint)]

_dll.pcap_open_live.restype = ctypes.c_void_p
_dll.pcap_open_live.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_char_p]
_dll.pcap_sendpacket.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
_dll.pcap_close.argtypes = [ctypes.c_void_p]
_dll.pcap_setdirection.argtypes = [ctypes.c_void_p, ctypes.c_int]
_dll.pcap_geterr.restype = ctypes.c_char_p
_dll.pcap_geterr.argtypes = [ctypes.c_void_p]
_dll.pcap_next_ex.argtypes = [ctypes.c_void_p,
                              ctypes.POINTER(ctypes.POINTER(_pkthdr)),
                              ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte))]
_dll.pcap_getevent.restype = ctypes.c_void_p
_dll.pcap_getevent.argtypes = [ctypes.c_void_p]
_dll.pcap_setnonblock.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]

# Npcap on Windows does not honour the pcap_open_live read timeout reliably:
# pcap_next_ex blocks until a packet arrives. Use non-blocking mode plus the
# waitable event handle so recv() can honour its own deadline.
_k32 = ctypes.WinDLL("kernel32.dll", use_last_error=True)
_k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
_k32.WaitForSingleObject.restype = ctypes.c_uint
_WAIT_OBJECT_0 = 0


def list_devices():
    """Return [(name, description), ...] for all non-loopback interfaces."""
    alldevs = ctypes.POINTER(_pcap_if_t)()
    eb = ctypes.create_string_buffer(256)
    if _dll.pcap_findalldevs(ctypes.byref(alldevs), eb) != 0:
        raise RuntimeError("pcap_findalldevs: " + eb.value.decode(errors="replace"))
    out = []
    p = alldevs
    while p:
        name = p.contents.name.decode(errors="replace")
        desc = (p.contents.description or b"").decode(errors="replace")
        out.append((name, desc))
        p = p.contents.next
    _dll.pcap_freealldevs(alldevs)
    return out


def find_device(substr):
    for name, desc in list_devices():
        if substr in desc:
            return name, desc
    raise RuntimeError("no interface matching %r" % substr)


def mac_to_bytes(s):
    return bytes.fromhex(s.replace("-", "").replace(":", ""))


class L2Socket(object):
    """Raw ethernet socket bound to one interface.

    direction: None (both), PCAP_D_IN (inbound only), PCAP_D_OUT (outbound only)
    """

    def __init__(self, dev_substr=None, dev_name=None, direction=None, snaplen=65536,
                 timeout_ms=50, promisc=False):
        if dev_name is None:
            dev_name, self.desc = find_device(dev_substr)
        else:
            self.desc = dev_name
        self.name = dev_name
        eb = ctypes.create_string_buffer(256)
        h = _dll.pcap_open_live(dev_name.encode(), snaplen, 1 if promisc else 0,
                                timeout_ms, eb)
        if not h:
            raise RuntimeError("pcap_open_live(%s): %s"
                               % (dev_name, eb.value.decode(errors="replace")))
        self._h = h
        if direction is not None:
            _dll.pcap_setdirection(h, direction)
        eb2 = ctypes.create_string_buffer(256)
        if _dll.pcap_setnonblock(h, 1, eb2) != 0:
            raise RuntimeError("pcap_setnonblock: " + eb2.value.decode(errors="replace"))
        self._ev = _dll.pcap_getevent(h)
        self.tx = 0
        self.rx = 0

    def send(self, wire):
        rc = _dll.pcap_sendpacket(self._h, wire, len(wire))
        if rc != 0:
            raise RuntimeError("send: " + _dll.pcap_geterr(self._h).decode(errors="replace"))
        self.tx += 1

    def recv(self, timeout_s=0.0):
        """Return (ts_epoch_float, bytes) or None after timeout_s seconds."""
        hdr = ctypes.POINTER(_pkthdr)()
        data = ctypes.POINTER(ctypes.c_ubyte)()
        deadline = time.perf_counter() + timeout_s
        while True:
            r = _dll.pcap_next_ex(self._h, ctypes.byref(hdr), ctypes.byref(data))
            if r == 1:
                ts = hdr.contents.ts.tv_sec + hdr.contents.ts.tv_usec / 1e6
                raw = bytes(bytearray(data[:hdr.contents.caplen]))
                self.rx += 1
                return ts, raw
            if r == 0:
                remain = deadline - time.perf_counter()
                if remain <= 0:
                    return None
                if self._ev:
                    _k32.WaitForSingleObject(self._ev, int(remain * 1000) + 1)
                else:
                    time.sleep(min(remain, 0.001))
                continue
            if r == -2:
                return None
            raise RuntimeError("pcap_next_ex rc=%d: %s"
                               % (r, _dll.pcap_geterr(self._h).decode(errors="replace")))

    def close(self):
        if self._h:
            _dll.pcap_close(self._h)
            self._h = None
            self._ev = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
