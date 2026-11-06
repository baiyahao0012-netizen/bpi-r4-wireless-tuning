# -*- coding: utf-8 -*-
"""Two-arm clock comparison: wall/wall vs frame/samples, 60 s each."""
import subprocess, sys, time, re, json

PY = sys.executable
HOST, USER, PWD = "192.168.240.221", "labuser", "[REDACTED-PWD]"
VIDEO = r"D:\Desktop\AI 辅助对话\test03_music.mp4"
ARMS = [("A", "wall", "wall"), ("B", "frame", "samples")]
SECS = 60

def receiver(tag):
    return ("cd /d C:\\rtc & python receiver.py --transport l2 --iface 8812BU "
            "--fb 1 --fb-iface I219 --fb-dst 40-C2-BA-52-70-95 "
            "--fb-src E8-80-88-BA-3C-BB --seconds %d --audio 1 --fps 25 "
            "--out-pcm rc_%s.pcm" % (SECS + 10, tag))

def one(tag, vpts, apts):
    r = subprocess.Popen([PY, "ctl.py", HOST, USER, PWD, receiver(tag)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(4.0)
    t0 = time.time()
    subprocess.run([PY, "sender.py", "--transport", "l2",
                    "--dst", "40-A5-EF-26-E3-47", "--src", "40-C2-BA-52-70-95",
                    "--fb-iface", "GbE", "--video", VIDEO,
                    "--width", "1280", "--height", "720", "--fps", "25",
                    "--seconds", str(SECS), "--bitrate", "3000000",
                    "--fec", "1", "--audio", "file",
                    "--audio-pts", apts, "--video-pts", vpts],
                   capture_output=True, timeout=SECS + 90)
    out = r.communicate(timeout=180)[0].decode("utf-8", "replace")
    d = {"arm": tag, "vpts": vpts, "apts": apts, "elapsed": round(time.time() - t0, 1)}
    m = re.search(r"drift (-?[\d.]+) ms", out);  d["drift_ms"] = float(m.group(1)) if m else None
    m = re.search(r"skew ms: p50=([\d.]+) p95=([\d.]+) \|max\|=([\d.]+)", out)
    if m: d["p50"], d["p95"], d["max"] = map(float, m.groups())
    m = re.search(r"video ok=(\d+) lost=(\d+) frame_loss=([\d.]+)%.*?decoded=(\d+).*?dec_err=(\d+)", out)
    if m: d["v_ok"], d["v_lost"], d["v_loss"], d["v_dec"], d["v_err"] = \
        int(m.group(1)), int(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5))
    m = re.search(r"audio ok=(\d+) lost=(\d+).*?decoded_samples=(\d+) \(([\d.]+) s\).*?dec_err_a=(\d+)", out)
    if m: d["a_ok"], d["a_lost"], d["a_sec"], d["a_err"] = \
        int(m.group(1)), int(m.group(2)), float(m.group(4)), int(m.group(5))
    return d

for tag, vpts, apts in ARMS:
    d = one(tag, vpts, apts)
    print(json.dumps(d, ensure_ascii=False), flush=True)
    time.sleep(5)
