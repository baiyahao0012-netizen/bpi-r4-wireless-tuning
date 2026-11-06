# -*- coding: utf-8 -*-
"""Calibrate the airtime-share threshold: 3 conditions x 3 reps."""
import subprocess, sys, time, re, json

PY = sys.executable
SELF_IP, EXT_IP = "192.168.240.232", "192.168.240.162"
REPS = 3

def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None

def run_sender(secs=10):
    args = [PY, "sender.py", "--transport", "l2",
            "--dst", "40-A5-EF-26-E3-47", "--src", "40-C2-BA-52-70-95",
            "--fb-iface", "GbE", "--video", "t01_640.mp4",
            "--width", "640", "--height", "480", "--fps", "30",
            "--seconds", str(secs), "--bitrate", "3000000",
            "--max-rate", "3000000", "--fec", "0", "--audio", "off",
            "--mac-ctl", "1"]
    p = subprocess.run(args, capture_output=True, text=True, timeout=200)
    return p.stdout

def parse(out):
    rows = []
    for line in out.splitlines():
        m = re.search(r"MACDBG q=(\d+)us rr=([\d.]+) share=([\d.]+) pkt=(\d+)", line)
        if m:
            rows.append((int(m.group(1)), float(m.group(3))))
    return rows

results = []
for rep in range(REPS):
    for name, dst in (("none", None), ("self", SELF_IP), ("external", EXT_IP)):
        bl = None
        if dst:
            bl = subprocess.Popen([PY, "blaster.py", dst, "13", "80"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
        try:
            out = run_sender(10)
        except Exception as e:
            out = ""
        if bl:
            try:
                bl.wait(timeout=30)
            except Exception:
                bl.kill()
        rows = parse(out)
        cong = [s for q, s in rows if q > 10000]
        base = [s for q, s in rows if q <= 10000]
        rec = {"case": name, "rep": rep, "n": len(rows),
               "n_cong": len(cong),
               "cong_med": med(cong), "cong_min": min(cong) if cong else None,
               "cong_max": max(cong) if cong else None,
               "base_med": med(base) if base else None}
        results.append(rec)
        print(json.dumps(rec), flush=True)
        time.sleep(2)

print("SUMMARY")
for name in ("none", "self", "external"):
    sel = [r for r in results if r["case"] == name and r["cong_med"] is not None]
    if not sel:
        print("%-9s no congestion samples" % name)
        continue
    cs = [r["cong_med"] for r in sel]
    print("%-9s n=%d  med_of_med=%.3f  min=%.3f  max=%.3f"
          % (name, len(sel), med(cs), min(cs), max(cs)), flush=True)
