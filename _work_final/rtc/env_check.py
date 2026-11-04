# -*- coding: utf-8 -*-
"""Step 1: environment check for RTC layer."""
import ctypes, ctypes.util, os, sys, time, platform

RESULT = []
def rec(name, ok, detail=""):
    RESULT.append((name, ok, detail))
    print(("[PASS] " if ok else "[FAIL] ") + name + ("  | " + str(detail) if detail else ""))

print("=" * 70)
print("Python:", sys.version.split()[0], "|", platform.platform())
print("=" * 70)

# ---------- 1. camera ----------
try:
    import cv2
    cams = []
    for i in range(4):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok, fr = cap.read()
            if ok and fr is not None:
                cams.append((i, fr.shape[1], fr.shape[0]))
            cap.release()
    rec("cv2 camera", len(cams) > 0, cams if cams else "no camera opened")
except Exception as e:
    rec("cv2 camera", False, repr(e))

# ---------- 2. microphone ----------
try:
    import sounddevice as sd, numpy as np
    ins = [(i, d['name'], int(d['default_samplerate']), d['max_input_channels'])
           for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0]
    detail = ins[:5]
    got = 0
    if ins:
        try:
            data = sd.rec(int(0.2 * 48000), samplerate=48000, channels=1, dtype='int16')
            sd.wait()
            got = int(np.abs(data).max())
        except Exception as e:
            detail = (detail, "rec err " + repr(e))
    rec("sounddevice mic", len(ins) > 0 and got >= 0, detail)
    print("      peak sample:", got)
except Exception as e:
    rec("sounddevice mic", False, repr(e))

# ---------- 3. PyAV encoders ----------
try:
    import av
    v = av.CodecContext.create('libx264', 'w')
    v.width, v.height, v.pix_fmt = 640, 480, 'yuv420p'
    v.time_base = av.Fraction(1, 30)
    v.options = {'preset': 'veryfast', 'tune': 'zerolatency', 'bitrate': '2000k'}
    v.open()
    pkts = 0
    for i in range(5):
        f = av.VideoFrame(640, 480, 'yuv420p')
        for p in f.planes:
            p.update(bytes([16 + i * 4] * p.buffer_size))
        f.pts = i
        for _ in v.encode(f):
            pkts += 1
    for _ in v.encode(None):
        pkts += 1
    rec("PyAV libx264", pkts > 0, "packets=%d" % pkts)
except Exception as e:
    rec("PyAV libx264", False, repr(e))

try:
    import av
    a = av.CodecContext.create('libopus', 'w')
    a.sample_rate = 48000
    a.layout = 'mono'
    a.format = 's16'
    a.bit_rate = 32000
    a.open()
    import numpy as np
    pk = 0
    for i in range(5):
        raw = (np.zeros(960, dtype=np.int16)).tobytes()
        af = av.AudioFrame(format='s16', layout='mono', samples=960)
        af.sample_rate = 48000
        af.planes[0].update(raw)
        af.pts = i
        for _ in a.encode(af):
            pk += 1
    rec("PyAV libopus", pk > 0, "packets=%d" % pk)
except Exception as e:
    rec("PyAV libopus", False, repr(e))

# ---------- 4. Npcap ----------
PCAP_IF_LOOPBACK = 0x00000001
class pcap_if_t(ctypes.Structure):
    pass
pcap_if_t._fields_ = [("next", ctypes.POINTER(pcap_if_t)),
                      ("name", ctypes.c_char_p),
                      ("description", ctypes.c_char_p),
                      ("addresses", ctypes.c_void_p),
                      ("flags", ctypes.c_uint)]

dll = None
for path in (r"C:\Windows\System32\Npcap\wpcap.dll", r"C:\Windows\System32\wpcap.dll"):
    if os.path.exists(path):
        try:
            dll = ctypes.WinDLL(path)
            break
        except Exception:
            pass
rec("Npcap wpcap.dll", dll is not None, "loaded" if dll else "not found")

devs = []
if dll:
    try:
        alldevs = ctypes.POINTER(pcap_if_t)()
        errbuf = ctypes.create_string_buffer(256)
        if dll.pcap_findalldevs(ctypes.byref(alldevs), errbuf) == 0:
            p = alldevs
            while p:
                nm = p.contents.name.decode(errors='replace') if p.contents.name else ""
                ds = p.contents.description.decode(errors='replace') if p.contents.description else ""
                fl = p.contents.flags
                if not (fl & PCAP_IF_LOOPBACK):
                    devs.append((nm, ds))
                p = p.contents.next
            dll.pcap_freealldevs(alldevs)
        rec("pcap_findalldevs", len(devs) > 0, "%d interfaces" % len(devs))
        for nm, ds in devs:
            print("      -", nm, "|", ds[:70])
    except Exception as e:
        rec("pcap_findalldevs", False, repr(e))

    for sym in ("pcap_setdirection", "pcap_sendpacket", "pcap_next_ex", "pcap_setnonblock", "pcap_getevent"):
        ok = hasattr(dll, sym)
        rec("npcap symbol %s" % sym, ok)

# ---------- 5. scapy ----------
try:
    from scapy.all import get_if_list, conf
    ifaces = get_if_list()
    rec("scapy get_if_list", len(ifaces) > 0, ifaces[:6])
except Exception as e:
    rec("scapy get_if_list", False, repr(e))

print("=" * 70)
bad = [n for n, ok, d in RESULT if not ok]
print("SUMMARY: %d checks, %d failed" % (len(RESULT), len(bad)))
if bad:
    print("FAILED:", bad)
print("=" * 70)
