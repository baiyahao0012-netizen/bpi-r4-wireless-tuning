#!/usr/bin/env python3
"""Case F: SR NTP<->RTP mapping and cross-stream drift from recorded runs.

Reads RESULT lines of receiver logs, uses sr_in_video / sr_in_audio records
(SSRC-mapped NTP + RTP timestamps) to check the RTP clock rate and the
cross-stream media-time drift.
"""
import glob
import json
import os
import statistics
import sys


def load_result(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("RESULT "):
            return json.loads(line[len("RESULT "):])
    return None


def secs(ntp):
    return ntp / 2 ** 32


def fit(records):
    if len(records) < 2:
        return None
    xs = [secs(r["ntp"]) for r in records]
    ys = [r["rtp_ts"] for r in records]
    x0 = xs[0]
    xs = [x - x0 for x in xs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return x0, my - b * mx, b


def main():
    d = sys.argv[1]
    rows = []
    for f in sorted(glob.glob(os.path.join(d, "*_rx.log"))):
        res = load_result(f)
        if not res:
            continue
        st = res.get("stats", {})
        fv = fit(st.get("sr_in_video") or [])
        fa = fit(st.get("sr_in_audio") or [])
        if not fv or not fa:
            continue
        tv, av, bv = fv
        ta, aa, ba = fa
        # cross-stream media time difference sampled at the video SR instants
        diffs = []
        for r in st["sr_in_video"]:
            t = secs(r["ntp"]) - ta
            diffs.append(r["rtp_ts"] / 90000.0 - (aa + ba * t) / 48000.0)
        rows.append({
            "file": os.path.basename(f),
            "video_rate": round(bv, 2),
            "audio_rate": round(ba, 2),
            "video_rate_err": round(bv - 90000, 3),
            "audio_rate_err": round(ba - 48000, 3),
            "drift_ms_30s": round((bv / 90000.0 - ba / 48000.0) * 30 * 1000, 3),
            "cross_stdev_ms": round(statistics.pstdev(diffs) * 1000, 3) if len(diffs) > 1 else None,
            "sr_video_n": len(st.get("sr_in_video") or []),
            "sr_audio_n": len(st.get("sr_in_audio") or []),
        })
    if not rows:
        print("no rows")
        return 1
    keys = list(rows[0].keys())
    print(",".join(keys))
    for r in rows:
        print(",".join(str(r.get(k, "")) for k in keys))
    vr = [r["video_rate"] for r in rows]
    ar = [r["audio_rate"] for r in rows]
    print("# summary: runs=%d video_rate mean=%.2f (expect 90000) audio_rate mean=%.2f (expect 48000)"
          % (len(rows), statistics.mean(vr), statistics.mean(ar)))
    print("# max |video err|=%.3f  max |audio err|=%.3f  max drift_30s=%.3f ms"
          % (max(abs(r["video_rate_err"]) for r in rows),
             max(abs(r["audio_rate_err"]) for r in rows),
             max(abs(r["drift_ms_30s"]) for r in rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
