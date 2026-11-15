"""NTP-style time probe client (run on the Pi)."""
import socket
import statistics
import struct
import time

SERVER = ("192.168.240.2", 9977)
offsets = []
rtts = []
for i in range(5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    s.connect(SERVER)
    t1 = time.time()
    s.sendall(struct.pack("!d", t1))
    data = s.recv(16)
    t4 = time.time()
    s.close()
    t2, t3 = struct.unpack("!dd", data)
    off = ((t2 - t1) + (t3 - t4)) / 2.0
    rtt = (t4 - t1) - (t3 - t2)
    offsets.append(off)
    rtts.append(rtt)
    print("sample %d offset_ms=%.3f rtt_ms=%.3f" % (i + 1, off * 1000, rtt * 1000), flush=True)
    time.sleep(0.2)

print("RESULT median_offset_ms=%.3f max_abs_offset_ms=%.3f median_rtt_ms=%.3f"
      % (statistics.median(offsets) * 1000,
         max(abs(x) for x in offsets) * 1000,
         statistics.median(rtts) * 1000), flush=True)
