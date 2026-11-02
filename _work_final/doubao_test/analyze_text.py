# -*- coding: utf-8 -*-
"""Text-stream analyzer v2 (PTS-based).

Measures, from a phone screen recording of a Doubao text answer:
  - t_send      : first big screen change after recording start (question bubble)
  - t_answer    : first sustained text activity after t_send
  - t_done      : last text activity
  - TTFT        : t_answer - t_send
  - answer_time : t_done - t_answer
  - stalls      : gaps between activity > STALL_MS (count / total / max)
Usage: python analyze_text.py <video.mp4> [--top f] [--bot f] [--csv out] [--stall-ms n]
"""
import sys, csv, av, argparse
import numpy as np

def decode(path):
    c = av.open(path); vs = c.streams.video[0]
    W, H = vs.codec_context.width, vs.codec_context.height
    out = []
    for f in c.decode(vs):
        t = f.time if f.time is not None else float(f.pts * vs.time_base)
        g = np.asarray(f.to_ndarray(format="gray"), dtype=np.uint8)
        out.append((t, g))
    return W, H, out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--top", type=float, default=0.07)
    ap.add_argument("--bot", type=float, default=0.72)
    ap.add_argument("--csv"); ap.add_argument("--stall-ms", type=int, default=300)
    ap.add_argument("--diff-thr", type=int, default=20)
    a = ap.parse_args()
    W, H, frames = decode(a.video)
    y0, y1 = int(H*a.top), int(H*a.bot)
    sig = []
    prev = None
    for t, g in frames:
        roi = g[y0:y1, :]
        textpx = int((roi < 140).sum())
        diff = 0 if prev is None else int((np.abs(roi.astype(np.int16) - prev.astype(np.int16)) > a.diff_thr).sum())
        sig.append((t, diff, textpx)); prev = roi
    dur = sig[-1][0]
    print("video %dx%d frames=%d dur=%.1fs ROI y=%d..%d" % (W, H, len(sig), dur, y0, y1))
    diffs = np.array([s[1] for s in sig], dtype=np.float64)
    mx = diffs.max()
    # activity = frame whose diff exceeds a small adaptive threshold
    thr = max(150.0, 0.06*mx)
    active = [sig[i][0] for i in range(len(sig)) if diffs[i] > thr]
    print("max_diff=%d  activity_thr=%.0f  active_frames=%d" % (mx, thr, len(active)))
    # cluster active times into bursts (gap > 400 ms starts a new burst)
    bursts = []
    for t in active:
        if bursts and t - bursts[-1][-1] <= 0.4:
            bursts[-1].append(t)
        else:
            bursts.append([t])
    # drop bursts shorter than 2 frames (noise)
    bursts = [b for b in bursts if len(b) >= 2]
    print("bursts:", [(round(b[0],2), round(b[-1],2), len(b)) for b in bursts])
    if bursts:
        t_send = bursts[0][0]
        ans = [b for b in bursts if b[0] > t_send + 0.2]
        t_answer = ans[0][0] if ans else None
        t_done = bursts[-1][-1]
        print("t_send=%.2f  t_answer=%s  t_done=%.2f" % (t_send, ("%.2f"%t_answer) if t_answer else "n/a", t_done))
        if t_answer:
            print("TTFT(send->first answer) = %.2f s" % (t_answer - t_send))
        print("answer window = %.2f s" % (t_done - (t_answer or t_send)))
    # stalls = gaps between consecutive active frames within the answer window
    if bursts:
        t0 = bursts[0][0]; t1 = bursts[-1][-1]
        win = [t for t in active if t0 <= t <= t1]
        gaps = [g2-g1 for g1, g2 in zip(win, win[1:]) if g2-g1 > a.stall_ms/1000.0]
        print("stalls >%dms within [%.1f,%.1f]: count=%d total=%.2fs max=%.2fs" % (
            a.stall_ms, t0, t1, len(gaps), sum(gaps), max(gaps) if gaps else 0))
        for g in sorted(gaps, reverse=True)[:8]:
            print("   stall %.2fs" % g)
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["t","diff_px","text_px"]); w.writerows(sig)
        print("CSV ->", a.csv)

if __name__ == "__main__":
    main()
