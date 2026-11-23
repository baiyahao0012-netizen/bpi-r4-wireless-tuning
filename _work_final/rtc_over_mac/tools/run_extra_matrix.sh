#!/bin/bash
# Regenerate raw evidence for: SRTCP, deterministic loss, 1080p paced.
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/file_av_lab.py
PROXY=/home/bai/rtc_test/l0/loss_proxy.py
CLIPS=/tmp/retest_clips
HD=/home/bai/rtc_test/testset_1080p
OUT=/tmp/extra
mkdir -p "$OUT"

echo "=== SRTCP ==="
F="${CLIPS}/1080p25_3_bbb_trailer_33s_10s.mp4"
python3 "$LAB" receiver --file "$F" --seconds 14 --srtp \
  --video-rtp-port 5602 --video-rtcp-port 5603 --video-feedback-port 5604 \
  --audio-rtp-port 5702 --audio-rtcp-port 5703 --audio-feedback-port 5704 > "$OUT/srtcp_rx.log" 2>&1 &
rp=$!
sleep 2
python3 "$LAB" sender --file "$F" --seconds 10 --srtp \
  --video-rtp-port 5602 --video-rtcp-port 5603 --video-feedback-port 5604 \
  --audio-rtp-port 5702 --audio-rtcp-port 5703 --audio-feedback-port 5704 > "$OUT/srtcp_tx.log" 2>&1
wait $rp 2>/dev/null
echo "SRTCP_DONE"

echo "=== DET LOSS ==="
det_arm() {  # clip idx arm rtx
  local clip="$1" idx="$2" arm="$3" rtx="${4:-}"
  local v_rtp=$((5200 + idx)) v_rtcp=$((5201 + idx)) v_fb=$((5202 + idx))
  local a_rtp=$((5300 + idx)) a_rtcp=$((5301 + idx)) a_fb=$((5302 + idx))
  local pv=$((6200 + idx)) pa=$((6300 + idx))
  local tag="det_${clip}_${arm}"
  local f="${CLIPS}/${clip}_10s.mp4"
  python3 "$LAB" receiver --file "$f" --seconds 16 \
      --video-rtp-port $v_rtp --video-rtcp-port $v_rtcp --video-feedback-port $v_fb \
      --audio-rtp-port $a_rtp --audio-rtcp-port $a_rtcp --audio-feedback-port $a_fb \
      ${rtx:+--video-rtx} > "$OUT/${tag}_rx.log" 2>&1 &
  local rp=$!
  sleep 1
  python3 "$PROXY" $pv 127.0.0.1 $v_rtp 20 1 20 > "$OUT/${tag}_pvid.json" 2>&1 &
  local ppv=$!
  python3 "$PROXY" $pa 127.0.0.1 $a_rtp 20 1 20 > "$OUT/${tag}_paud.json" 2>&1 &
  local ppa=$!
  sleep 1
  python3 "$LAB" sender --file "$f" --seconds 12 \
      --video-rtp-port $pv --video-rtcp-port $v_rtcp --video-feedback-port $v_fb \
      --audio-rtp-port $pa --audio-rtcp-port $a_rtcp --audio-feedback-port $a_fb \
      ${rtx:+--video-rtx} > "$OUT/${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null || true; wait $ppv 2>/dev/null || true; wait $ppa 2>/dev/null || true
  echo "DONE ${tag}"
}
det_arm 1080p25_3_bbb_trailer_33s 2 "rtx_on_a" "1"
det_arm 1080p25_3_bbb_trailer_33s 2 "rtx_on_b" "1"
det_arm 1080p25_3_bbb_trailer_33s 2 "rtx_off_a"
echo "DET_DONE"

echo "=== 1080P PACED ==="
hd_arm() {
  local tag="$1" f="$2"
  python3 "$LAB" receiver --file "$f" --seconds 26 \
      --video-rtp-port 5802 --video-rtcp-port 5803 --video-feedback-port 5804 \
      --audio-rtp-port 5902 --audio-rtcp-port 5903 --audio-feedback-port 5904 > "$OUT/hd_${tag}_rx.log" 2>&1 &
  local rp=$!
  sleep 2
  python3 "$LAB" sender --file "$f" --seconds 22 --pace \
      --video-rtp-port 5802 --video-rtcp-port 5803 --video-feedback-port 5804 \
      --audio-rtp-port 5902 --audio-rtcp-port 5903 --audio-feedback-port 5904 > "$OUT/hd_${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null
  echo "DONE hd_${tag}"
}
hd_arm bbb "${HD}/1080p25_3_bbb_trailer_33s.mp4"
hd_arm sintel "${HD}/1080p24_1_sintel_trailer_52s.mp4"
hd_arm artemis "${HD}/1080p30_1_artemis_origins_85s.mp4"
echo EXTRA_DONE
