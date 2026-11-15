#!/bin/bash
# T7 V1 matrix: A(no loss) / B(5% loss, RTX on) / C(5% loss, RTX off), 3 reps each.
# Prints one "ARM <tag> <role> <json>" line per run for offline parsing.
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/t7_rtx_lab.py
CLIP=/home/bai/rtc_test/clip10.mp4

run_arm() {
  local tag="$1" loss="$2" flag="$3"
  rm -f /tmp/m_rx_${tag}.log /tmp/m_tx_${tag}.log
  python3 "$LAB" receiver --seconds 16 --latency 500 --loss "$loss" $flag \
      > "/tmp/m_rx_${tag}.log" 2>&1 &
  local rpid=$!
  sleep 2
  python3 "$LAB" sender --file "$CLIP" --loss "$loss" --seconds 11 \
      > "/tmp/m_tx_${tag}.log" 2>&1
  # receiver window is 16s and quits at 21s
  sleep 11
  local rx tx
  rx=$(grep -m1 '^RESULT' "/tmp/m_rx_${tag}.log" || true)
  tx=$(grep -m1 '^RESULT' "/tmp/m_tx_${tag}.log" || true)
  echo "ARM ${tag} receiver ${rx#RESULT }"
  echo "ARM ${tag} sender ${tx#RESULT }"
  wait $rpid 2>/dev/null || true
}

for i in 1 2 3; do
  run_arm "A${i}" 0.0 ""
done
for i in 1 2 3; do
  run_arm "B${i}" 0.05 ""
done
for i in 1 2 3; do
  run_arm "C${i}" 0.05 "--no-rtx"
done
echo MATRIX_DONE
