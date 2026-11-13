# -*- coding: utf-8 -*-
"""
生成音画锚点（打板）测试素材：
  - 1920x1080, 30 fps, 10 s, H.264 High + Opus 48kHz 立体声, MKV
  - 每 1.000 s：一整帧纯白（视频锚点）
  - 每 1.000 s：50 ms 的 1 kHz 短音（音频锚点），与白帧同刻
  - 固定 GOP=30，每帧白闪对齐一个 I 帧（抗丢包更稳）
生成后自检：白帧数、白帧时刻、短音起止时刻、音画锚点是否对齐。
"""
import os, re, subprocess, sys, wave, struct, math
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

BASE = r"D:\Desktop\AI 辅助对话\_work_final\rtc\media"
OUT_DIR = r"D:\Desktop\AI 辅助对话\_work_final\rtc\media\testset_1080p"
OUT = os.path.join(OUT_DIR, "anchor_1080p30_clapper_10s.mkv")
TMP_WAV = os.path.join(BASE, "_anchor_check.wav")

DUR = 10
FPS = 30
SR = 48000

def run(args, capture=False):
    print("\n$", " ".join('"%s"' % a if " " in a else a for a in args[1:]))
    p = subprocess.run(args, capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print(p.stderr[-2000:])
        sys.exit(1)
    return p

# 1) 生成素材
enable_v = r"lt(mod(n\,30)\,1)"
volume_a = r"if(lt(mod(t\,1)\,0.05)\,1\,0)"
filter_complex = (
    "[0:v]drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable=%s[v];"
    "[1:a]volume=%s:eval=frame,pan=stereo|c0=c0|c1=c0[a]"
) % (enable_v, volume_a)

args = [
    FFMPEG, "-y",
    "-f", "lavfi", "-i", "color=black:s=1920x1080:r=%d:d=%d" % (FPS, DUR),
    "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=%d:duration=%d" % (SR, DUR),
    "-filter_complex", filter_complex,
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
    "-preset", "medium", "-crf", "18", "-bf", "0",
    "-x264-params", "keyint=30:min-keyint=30:scenecut=0",
    "-c:a", "libopus", "-b:a", "128k", "-ar", str(SR), "-ac", "2",
    "-f", "matroska", OUT,
]
run(args)
print("\n=== 生成完成:", OUT, os.path.getsize(OUT), "bytes")

# 2) 流信息（ffmpeg -i 的 stderr）
p = run([FFMPEG, "-i", OUT, "-f", "null", "-"], capture=True)
for line in p.stderr.splitlines():
    if re.search(r"Stream|Duration|Video:|Audio:", line):
        print(line.strip())

# 3) 视频自检：逐帧平均亮度，找白帧
p = run([FFMPEG, "-i", OUT, "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
         "-f", "null", "-"], capture=True)
white, black, cur_t = [], [], None
for line in p.stdout.splitlines():
    m_t = re.search(r"pts_time:([\d.]+)", line)
    if m_t:
        cur_t = float(m_t.group(1)); continue
    m_y = re.search(r"YAVG=([\d.]+)", line)
    if m_y and cur_t is not None:
        y = float(m_y.group(1))
        if y > 200: white.append(cur_t)      # tv 范围白=235
        elif y < 40: black.append(cur_t)     # tv 范围黑=16
        cur_t = None
print("\n=== 视频锚点 ===")
print("白帧数:", len(white), " 黑帧数:", len(black))
print("白帧时刻:", ["%.3f" % t for t in white])

# 4) 音频自检：解码单声道 WAV，按 20 ms 窗找短音起止
run([FFMPEG, "-y", "-i", OUT, "-vn", "-ac", "1", "-ar", "8000", "-f", "wav", TMP_WAV], capture=True)
w = wave.open(TMP_WAV, "rb")
n, sw, ch, rate = w.getnframes(), w.getsampwidth(), w.getnchannels(), w.getframerate()
raw = w.readframes(n)
w.close()
samples = struct.unpack("<%dh" % n, raw)
win = int(rate * 0.02)
bursts, in_b, start = [], False, 0.0
for i in range(0, n, win):
    seg = samples[i:i+win]
    rms = math.sqrt(sum(x*x for x in seg)/len(seg)) if seg else 0
    if rms > 1500 and not in_b:
        in_b, start = True, i/rate
    elif rms <= 1500 and in_b:
        in_b, end = False, i/rate
        bursts.append((round(start,3), round(end,3)))
if in_b: bursts.append((round(start,3), round(n/rate,3)))
print("\n=== 音频锚点 ===")
print("短音段数:", len(bursts))
for s,e in bursts: print("  短音 %.3f - %.3f s (%.0f ms)" % (s,e,(e-s)*1000))

# 5) 音画对齐核对
print("\n=== 对齐核对（期望 0,1,2,...,9 s 各一对）===")
vt = [round(t) for t in white]
at = [round(s) for s,_ in bursts]
print("视频锚点整秒:", vt)
print("音频锚点整秒:", at)
print("对齐:", "OK" if vt == at == list(range(DUR)) else "MISMATCH")

os.remove(TMP_WAV)
