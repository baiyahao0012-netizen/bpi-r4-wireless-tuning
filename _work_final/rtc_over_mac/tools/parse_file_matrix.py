#!/usr/bin/env python3
"""Summarise file_av_lab.py runs (res.py RESULT lines) into a CSV.

Usage: parse_file_matrix.py <log_dir> <case> <out_csv>
Expected video frames per clip: 24fps->240, 25fps->250, 30fps->300.
"""
import glob
import json
import os
import re
import sys

EXPECTED = {"1080p24": 240, "1080p25": 250, "1080p30": 300}


def load_result(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("RESULT "):
                    return json.loads(line[len("RESULT "):])
    except (OSError, json.JSONDecodeError):
        pass
    return None


def jb_fields(stats):
    out = {}
    for k, v in stats.items():
        if k.startswith("jb_") and isinstance(v, dict):
            for f in ("num-lost", "num-late", "num-duplicates", "rtx-success-count", "num-pushed"):
                out[f] = out.get(f, 0) + int(v.get(f, 0) or 0)
    return out


def rtx_mid(stats, tag):
    d = stats.get(tag + "_mid") or {}
    return d if isinstance(d, dict) else {}


def main():
    log_dir, case, out_csv = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = []
    for rx in sorted(glob.glob(os.path.join(log_dir, case + "_*_rx.log"))):
        tag = os.path.basename(rx)[: -len("_rx.log")]
        m = re.match(r"([A-E])_(.+)_((?:rtx|artx|pli)_(?:on|off)|srtp)_r(\d+)$", tag)
        if m:
            clip, arm, run = m.group(2), m.group(3), "r" + m.group(4)
        else:
            m = re.match(r"([A-E])_(.+)_r(\d+)$", tag)
            if m:
                clip, arm, run = m.group(2), "base", "r" + m.group(3)
            else:
                clip, arm, run = tag, "", ""
        res = load_result(rx)
        if res is None:
            rows.append({"clip": clip, "case": case, "arm": arm, "run": "", "error": "no RESULT"})
            continue
        st = res.get("stats", {})
        tx_res = load_result(rx.replace("_rx.log", "_tx.log"))
        tx = (tx_res or {}).get("stats", {})
        jb = jb_fields(st)
        rtx = rtx_mid(st, "rx0")
        artx = rtx_mid(st, "rx1")
        fps_key = clip[:7]
        expected = EXPECTED.get(fps_key, 0)
        rows.append({
            "clip": clip,
            "case": case,
            "arm": arm,
            "run": run,
            "video_frames": st.get("video_frames", ""),
            "expected_frames": expected,
            "audio_buffers": st.get("audio_buffers", ""),
            "audio_samples": st.get("audio_samples", ""),
            "net_pt96": st.get("net_video_pt96", ""),
            "net_pt97": st.get("net_video_pt97", ""),
            "in_pt96": st.get("in_video_pt96", ""),
            "in_pt97": st.get("in_video_pt97", ""),
            "assoc": rtx.get("num-rtx-assoc-packets", rtx.get("assoc", "")),
            "rtx_requests": rtx.get("requests", ""),
            "rtx_packets": rtx.get("packets", ""),
            "rtx_success": jb.get("rtx-success-count", ""),
            "jb_lost": jb.get("num-lost", ""),
            "jb_late": jb.get("num-late", ""),
            "jb_dup": jb.get("num-duplicates", ""),
            "nack": st.get("rtcp_out0_NACK", ""),
            "rr": st.get("rtcp_out0_RR", ""),
            "pli": st.get("rtcp_out0_PLI", ""),
            "sr_video": len(st.get("sr_in_video", []) or []),
            "sr_audio": len(st.get("sr_in_audio", []) or []),
            "a_net111": st.get("net_audio_pt111", ""),
            "a_in111": st.get("in_audio_pt111", ""),
            "a_net112": st.get("net_audio_pt112", ""),
            "a_in112": st.get("in_audio_pt112", ""),
            "a_assoc": artx.get("num-rtx-assoc-packets", artx.get("assoc", "")),
            "a_rtx_pkts": artx.get("packets", ""),
            "tx_pli": tx.get("rtcp_in_video_PLI", ""),
            "rx_pli": st.get("rtcp_out0_PLI", ""),
            "kf_sink": tx.get("keyframe_events_encoder_sink", ""),
            "kf_src": tx.get("keyframe_events_encoder_src", ""),
            "idr_aus": tx.get("idr_aus", ""),
            "idr_500ms": tx.get("idrs_within_500ms_after_event", ""),
            "tx_errors": ";".join(map(str, tx.get("errors", [])))[:120],
            "errors": ";".join(map(str, st.get("errors", [])))[:200],
        })
    if not rows:
        print("no rows for", case)
        return 1
    keys = list(rows[0].keys())
    for r in rows:
        for k in keys:
            r.setdefault(k, "")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(str(r.get(k, "")) for k in keys) + "\n")
    print("wrote", out_csv, len(rows), "rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())



