#!/bin/bash
# Deterministic loss matrix: loss_proxy.py drops every <mod>-th packet's first <drop>.
# Same modifier/drop on both video and audio => fully reproducible loss pattern.
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/file_av_lab.py
PROXY=/home/bai/rtc_test/l0/loss_proxy.py
CLIPS=/tmp/retest_clips
OUT=/tmp/fa_det
MOD="${1:-20}"
DROP="${2:-1}"
mkdir -p "$OUT"

run_arm() {  # clip idx arm rtx
  local clip="$1" idx="$2" arm="$3" rtx="$4"
  local v_rtp=$((5200 + idx)) v_rtcp=$((5201 + idx)) v_fb=$((5202 + idx))
  local a_rtp=$((5300 + idx)) a_rtcp=$((5301 + idx)) a_fb=$((5302 + idx))
  local pv=$((6200 + idx)) pa=$((6300 + idx))
  local tag="det_${clip}_${arm}"
  local f="${CLIPS}/${clip}_10s.mp4"
  rm -f "$OUT/${tag}"_*.log
  python3 "$LAB" receiver --file "$f" --seconds 16 \
      --video-rtp-port $v_rtp --video-rtcp-port $v_rtcp --video-feedback-port $v_fb \
      --audio-rtp-port $a_rtp --audio-rtcp-port $a_rtcp --audio-feedback-port $a_fb \
      ${rtx:+--video-rtx} > "$OUT/${tag}_rx.log" 2>&1 &
  local rp=$!
  sleep 1
  python3 "$PROXY" $pv 127.0.0.1 $v_rtp $MOD $DROP 20 > "$OUT/${tag}_pvid.json" 2>&1 &
  local ppv=$!
  python3 "$PROXY" $pa 127.0.0.1 $a_rtp $MOD $DROP 20 > "$OUT/${tag}_paud.json" 2>&1 &
  local ppa=$!
  sleep 1
  python3 "$LAB" sender --file "$f" --seconds 12 \
      --video-rtp-port $pv --video-rtcp-port $v_rtcp --video-feedback-port $v_fb \
      --audio-rtp-port $pa --audio-rtcp-port $a_rtcp --audio-feedback-port $a_fb \
      ${rtx:+--video-rtx} > "$OUT/${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null || true
  wait $ppv 2>/dev/null || true
  wait $ppa 2>/dev/null || true
  echo "DONE ${tag}"
}

run_arm 1080p25_3_bbb_trailer_33s 2 "rtx_on_a" "1"
run_arm 1080p25_3_bbb_trailer_33s 2 "rtx_on_b" "1"
run_arm 1080p25_3_bbb_trailer_33s 2 "rtx_off_a" ""
run_arm 1080p30_1_artemis_origins_85s 3 "rtx_on_a" "1"
echo DET_DONE
