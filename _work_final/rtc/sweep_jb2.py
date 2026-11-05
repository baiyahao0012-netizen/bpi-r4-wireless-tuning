# -*- coding: utf-8 -*-
"""Choose the jitter-buffer ceiling from data: 4 depths x 3 reps under burst loss."""
import subprocess, sys, time, re, json

PY = sys.executable
HOST, USER, PWD = "192.168.240.221", "labuser", "[REDACTED-PWD]"
VIDEO = r"D:\Desktop\AI 辅助对话\_work_final\rtc\t01_640.mp4"
AUDIO = r"D:\Desktop\AI 辅助对话\test.mp4"
VALUES = [40, 60, 100, 200]
REPS = 3

def receiver(jb, tag):
    return ("cd /d C:\\rtc & python receiver.py --transport l2 --iface 8812BU "
            "--fb 1 --fb-iface I219 --fb-dst 40-C2-BA-52-70-95 "
            "--fb-src E8-80-88-BA-3C-BB --seconds 36 --audio 1 --fps 30 "
            "--burst 50 --jb-max %d --out r_%s.h264" % (jb, tag))

def one(jb, tag):
    r = subprocess.Popen([PY, "ctl.py", HOST, USER, PWD, receiver(jb, tag)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(4.0)
    subprocess.run([PY, "sender.py", "--transport", "l2",
                    "--dst", "40-A5-EF-26-E3-47", "--src", "40-C2-BA-52-70-95",
                    "--fb-iface", "GbE", "--video", VIDEO, "--audio-file", AUDIO,
                    "--width", "640", "--height", "480", "--fps", "30",
                    "--seconds", "28", "--bitrate", "2000000", "--fec", "1",
                    "--audio", "file", "--audio-pts", "samples"],
                   capture_output=True, timeout=200)
    out = r.communicate(timeout=180)[0].decode("utf-8", "replace")
    d = {"jb": jb, "tag": tag}
    m = re.search(r"drift (-?[\d.]+) ms", out);            d["drift"] = float(m.group(1)) if m else None
    m = re.search(r"skew ms: p50=([\d.]+) p95=([\d.]+) \|max\|=([\d.]+)", out)
    if m: d["p50"], d["p95"], d["max"] = map(float, m.groups())
    m = re.search(r"video ok=(\d+) lost=(\d+) frame_loss=([\d.]+)%.*?decoded=(\d+).*?dec_err=(\d+)", out)
    if m: d["v_ok"], d["v_lost"], d["v_loss"], d["v_dec"], d["v_err"] = \
        int(m.group(1)), int(m.group(2)), float(m.group(3)), int(m.group(4)), int(m.group(5))
    m = re.search(r"audio ok=(\d+) lost=(\d+).*?dec_err_a=(\d+)", out)
    if m: d["a_ok"], d["a_lost"], d["a_err"] = int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.search(r"D=(\d+)ms\s+video late=(\d+) under=(\d+)\s+audio late=(\d+) under=(\d+)", out)
    if m: d["D"], d["v_late"], d["v_under"], d["a_late"], d["a_under"] = map(int, m.groups())
    m = re.search(r"recovery: fec_recovered=(\d+) nack_sent=(\d+) pli_sent=(\d+)", out)
    if m: d["fec"], d["nack"], d["pli"] = map(int, m.groups())
    return d

rows = []
for rep in range(REPS):
    for jb in VALUES:
        tag = "b%d_%d" % (jb, rep)
        try:
            d = one(jb, tag)
        except Exception as e:
            d = {"jb": jb, "tag": tag, "error": repr(e)}
        rows.append(d)
        print(json.dumps(d, ensure_ascii=False), flush=True)
        time.sleep(3)

print("SUMMARY")
def med(sel, k):
    v = sorted(x[k] for x in sel if x.get(k) is not None)
    return v[len(v)//2] if v else None
for jb in VALUES:
    sel = [r for r in rows if r.get("jb") == jb and r.get("p95") is not None]
    if not sel: 
        print("jb=%d  no data" % jb); continue
    print("jb=%-4d n=%d D=%s v_loss=%s v_dec=%s v_err=%s p50=%s p95=%s max=%s drift=%s a_lost=%s"
          % (jb, len(sel), med(sel,"D"), med(sel,"v_loss"), med(sel,"v_dec"),
             med(sel,"v_err"), med(sel,"p50"), med(sel,"p95"), med(sel,"max"),
             med(sel,"drift"), sum(x.get("a_lost",0) for x in sel)), flush=True)
