# -*- coding: utf-8 -*-
"""5-minute stability run: alternate 60s congestion / 60s idle on 2.4G."""
import subprocess, sys, time, re, json, os

PY = sys.executable
DUR = 300
LOGS = "long_sender.log"

sender_args = [PY, "sender.py", "--transport", "l2",
               "--dst", "40-A5-EF-26-E3-47", "--src", "40-C2-BA-52-70-95",
               "--fb-iface", "GbE", "--video", "t01_640.mp4",
               "--width", "640", "--height", "480", "--fps", "30",
               "--seconds", str(DUR), "--bitrate", "2000000",
               "--max-rate", "4000000", "--min-rate", "500000",
               "--fec", "1", "--audio", "off", "--mac-ctl", "1"]

fh = open(LOGS, "w", encoding="utf-8", errors="replace")
sender = subprocess.Popen(sender_args, stdout=fh, stderr=subprocess.STDOUT)
t0 = time.time()
marks = []
cyc = 0
while time.time() - t0 < DUR - 80:
    cyc += 1
    marks.append(("load_start", time.time() - t0, cyc))
    bl = subprocess.Popen([PY, "blaster.py", "192.168.240.232", "60", "80"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(62)
    try:
        bl.wait(timeout=20)
    except Exception:
        bl.kill()
    marks.append(("load_end", time.time() - t0, cyc))
    time.sleep(58)
sender.wait()
fh.close()
print(json.dumps(marks), flush=True)

# ---- analysis -----------------------------------------------------------
lines = open(LOGS, encoding="utf-8", errors="replace").read().splitlines()
dbg = []
for ln in lines:
    m = re.search(r"MACDBG q=(\d+)us rr=([\d.]+) share=([\d.]+) pkt=(\d+)", ln)
    if m:
        dbg.append({"q": int(m.group(1)), "rr": float(m.group(2)),
                    "share": float(m.group(3)), "pkt": int(m.group(4))})
ctl = [ln.strip() for ln in lines if "MAC-CTL" in ln]

def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None

cong = [d for d in dbg if d["q"] > 10000 and d["pkt"] > 0]
idle = [d for d in dbg if d["q"] <= 10000]
print("samples=%d  congested=%d  idle=%d" % (len(dbg), len(cong), len(idle)), flush=True)
if cong:
    s = [d["share"] for d in cong]
    print("CONG share  med=%.2f min=%.2f max=%.2f   q med=%d"
          % (med(s), min(s), max(s), med([d["q"] for d in cong])), flush=True)
if idle:
    s = [d["share"] for d in idle]
    print("IDLE share  med=%.2f min=%.2f max=%.2f"
          % (med(s), min(s), max(s)), flush=True)
print("rate changes=%d" % len(ctl), flush=True)
for c in ctl:
    print("  " + c, flush=True)
