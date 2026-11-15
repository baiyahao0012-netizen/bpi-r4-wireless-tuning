#!/bin/bash
# T7 latency x rtx-retry-period sweep at 5% loss.
# For each jitterbuffer latency: one no-RTX arm (baseline) + three RTX-on arms.
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/t7_rtx_lab.py
CLIP=/home/bai/rtc_test/clip10.mp4

run_case() {
  local tag="$1"; shift
  rm -f /tmp/sw_rx_${tag}.log /tmp/sw_tx_${tag}.log
  python3 "$LAB" receiver --seconds 18 "$@" > "/tmp/sw_rx_${tag}.log" 2>&1 &
  local rp=$!
  sleep 2
  python3 "$LAB" sender --file "$CLIP" --loss 0.05 --seconds 11 \
      > "/tmp/sw_tx_${tag}.log" 2>&1
  wait $rp 2>/dev/null || true
  local rx
  rx=$(grep -m1 '^RESULT' "/tmp/sw_rx_${tag}.log" || true)
  echo "SWEEP ${tag} ${rx#RESULT }"
}

for LAT in 500 800 1200 1500; do
  run_case "C_lat${LAT}" --latency "$LAT" --no-rtx
  for P in 300 600 1000; do
    run_case "B_lat${LAT}_p${P}" --latency "$LAT" --rtx-retry-period "$P" \
        --rtx-retry-timeout 200 --rtcp-min-interval 100000000
  done
done
echo SWEEP_DONE
