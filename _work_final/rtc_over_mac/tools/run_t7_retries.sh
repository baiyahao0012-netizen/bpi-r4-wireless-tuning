#!/bin/bash
# rtx-max-retries sweep 1..10, 4 rounds each, frozen T7 config.
# Raw RESULT JSON kept in /tmp/t7retry_<n>_<i>.json
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/t7_rtx_lab.py
CLIP=/home/bai/rtc_test/clip10.mp4
COMMON="--latency 500 --loss 0.05 --rtx-retry-period 600 --rtx-retry-timeout 200 --bandwidth 1000000 --rtcp-min-interval 100000000"

run_one() {
  local n="$1" i="$2"
  local tag="r${n}_${i}"
  rm -f "/tmp/t7retry_${tag}.json" "/tmp/t7retry_${tag}.log"
  python3 "$LAB" receiver --seconds 18 $COMMON --rtx-max-retries "$n" \
      > "/tmp/t7retry_${tag}.log" 2>&1 &
  local rp=$!
  sleep 2
  python3 "$LAB" sender --file "$CLIP" --loss 0.05 --seconds 11 \
      > "/tmp/t7retry_${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null || true
  grep -m1 '^RESULT' "/tmp/t7retry_${tag}.log" | sed 's/^RESULT //' > "/tmp/t7retry_${tag}.json"
  local dec assoc succ lost
  dec=$(grep -o '"decoded_frames": [0-9]*' "/tmp/t7retry_${tag}.json" | head -1 | grep -o '[0-9]*')
  assoc=$(grep -o '"assoc": [0-9]*' "/tmp/t7retry_${tag}.json" | head -1 | grep -o '[0-9]*')
  succ=$(grep -o '"rtx-success-count": [0-9]*' "/tmp/t7retry_${tag}.json" | head -1 | grep -o '[0-9]*')
  lost=$(grep -o '"num-lost": [0-9]*' "/tmp/t7retry_${tag}.json" | head -1 | grep -o '[0-9]*')
  echo "RETRY ${n} ${i} ${dec} ${assoc} ${succ} ${lost}"
}

for n in 1 2 3 4 5 6 7 8 9 10; do
  for i in 1 2 3 4; do
    run_one "$n" "$i"
  done
done
echo RETRY_SWEEP_DONE
