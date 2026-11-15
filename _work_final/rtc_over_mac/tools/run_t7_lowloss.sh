#!/bin/bash
# T7 V1 low-loss matrix: 0.1% loss, RTX on (D) vs off (E), 3 reps each.
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/t7_rtx_lab.py
CLIP=/home/bai/rtc_test/clip10.mp4

run_arm() {
  local tag="$1" loss="$2" flag="$3"
  rm -f /tmp/m_rx_${tag}.log /tmp/m_tx_${tag}.log
  python3 "$LAB" receiver --seconds 16 --latency 500 --loss "$loss" $flag > "/tmp/m_rx_${tag}.log" 2>&1 &
  local rpid=$!
  sleep 2
  python3 "$LAB" sender --file "$CLIP" --loss "$loss" --seconds 11 > "/tmp/m_tx_${tag}.log" 2>&1
  wait $rpid 2>/dev/null || true
}

for i in 1 2 3; do run_arm "D${i}" 0.001 ""; done
for i in 1 2 3; do run_arm "E${i}" 0.001 "--no-rtx"; done
echo LOWLOSS_DONE
