#!/bin/bash
# Six-clip matrix runner for file_av_lab.py (HANDOFF_FILE_RETEST_20261115 case A-E).
# Usage: run_file_matrix.sh <case> [rounds]
#   case: A | B | C | D | E
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/file_av_lab.py
CLIPS=/tmp/retest_clips
OUT=/tmp/fa_out
mkdir -p "$OUT"
CASE="${1:-A}"
ROUNDS="${2:-1}"
CLIP_LIST="1080p24_1_sintel_trailer_52s 1080p24_2_caminandes_90s 1080p25_3_bbb_trailer_33s 1080p30_1_artemis_origins_85s 1080p30_2_artemis_avatar_76s 1080p30_3_artemis_recap_90s"

idx_of() {
  case "$1" in
    1080p24_1_sintel_trailer_52s) echo 0 ;;
    1080p24_2_caminandes_90s) echo 1 ;;
    1080p25_3_bbb_trailer_33s) echo 2 ;;
    1080p30_1_artemis_origins_85s) echo 3 ;;
    1080p30_2_artemis_avatar_76s) echo 4 ;;
    1080p30_3_artemis_recap_90s) echo 5 ;;
  esac
}

run_arm() {  # clip idx case arm extra_sender extra_receiver
  local clip="$1" idx="$2" case="$3" arm="$4" sx="$5" rx="$6"
  local v_rtp=$((5200 + idx)) v_rtcp=$((5201 + idx)) v_fb=$((5202 + idx))
  local a_rtp=$((5300 + idx)) a_rtcp=$((5301 + idx)) a_fb=$((5302 + idx))
  local tag="${case}_${clip}_${arm}"
  local f="${CLIPS}/${clip}_10s.mp4"
  rm -f "$OUT/${tag}_rx.log" "$OUT/${tag}_tx.log"
  python3 "$LAB" receiver --file "$f" --seconds 14 \
      --video-rtp-port $v_rtp --video-rtcp-port $v_rtcp --video-feedback-port $v_fb \
      --audio-rtp-port $a_rtp --audio-rtcp-port $a_rtcp --audio-feedback-port $a_fb \
      $rx > "$OUT/${tag}_rx.log" 2>&1 &
  local rp=$!
  sleep 2
  python3 "$LAB" sender --file "$f" --seconds 10 \
      --video-rtp-port $v_rtp --video-rtcp-port $v_rtcp --video-feedback-port $v_fb \
      --audio-rtp-port $a_rtp --audio-rtcp-port $a_rtcp --audio-feedback-port $a_fb \
      $sx > "$OUT/${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null || true
  local ok="RESULT_OK"
  grep -q '^RESULT' "$OUT/${tag}_rx.log" || ok="RECV_NO_RESULT"
  grep -q '^RESULT' "$OUT/${tag}_tx.log" || ok="$ok TX_NO_RESULT"
  echo "DONE ${tag} ${ok}"
}

for clip in $CLIP_LIST; do
  idx=$(idx_of "$clip")
  for r in $(seq 1 "$ROUNDS"); do
    case "$CASE" in
      A)
        run_arm "$clip" "$idx" "A" "r${r}" "" "" ;;
      B)
        run_arm "$clip" "$idx" "B" "rtx_on_r${r}" "--video-rtx --video-loss 0.05" "--video-rtx"
        run_arm "$clip" "$idx" "B" "rtx_off_r${r}" "--video-loss 0.05" "" ;;
      C)
        run_arm "$clip" "$idx" "C" "artx_on_r${r}" "--audio-rtx --audio-loss 0.05" "--audio-rtx"
        run_arm "$clip" "$idx" "C" "artx_off_r${r}" "--audio-loss 0.05" "" ;;
      D)
        run_arm "$clip" "$idx" "D" "pli_on_r${r}" "--reencode-video --video-loss 0.05 --pace" "--force-keyframe"
        run_arm "$clip" "$idx" "D" "pli_off_r${r}" "--reencode-video --video-loss 0.05 --pace" "" ;;
      E)
        run_arm "$clip" "$idx" "E" "srtp_r${r}" "--srtp" "--srtp" ;;
    esac
  done
done
echo MATRIX_DONE
