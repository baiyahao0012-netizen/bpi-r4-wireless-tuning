#!/bin/bash
# T7 freeze evidence: 6 runs of the bandwidth=1e6 config, then 6 with a NACK
# retry cap. Raw RESULT JSON of each receiver is kept in /tmp/t7freeze_<tag>.json
set -u
export LC_ALL=C
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LAB=/tmp/t7_rtx_lab.py
CLIP=/home/bai/rtc_test/clip10.mp4
COMMON="--latency 500 --loss 0.05 --rtx-retry-period 600 --rtx-retry-timeout 200 --bandwidth 1000000 --rtcp-min-interval 100000000"

run_case() {
  local tag="$1"; shift
  rm -f /tmp/t7freeze_${tag}.json /tmp/t7freeze_${tag}.log
  python3 "$LAB" receiver --seconds 18 $COMMON "$@" > "/tmp/t7freeze_${tag}.log" 2>&1 &
  local rp=$!
  sleep 2
  python3 "$LAB" sender --file "$CLIP" --loss 0.05 --seconds 11 > "/tmp/t7freeze_${tag}_tx.log" 2>&1
  wait $rp 2>/dev/null || true
  grep -m1 '^RESULT' "/tmp/t7freeze_${tag}.log" | sed 's/^RESULT //' > "/tmp/t7freeze_${tag}.json"
  echo "FREEZE ${tag} $(cat /tmp/t7freeze_${tag}.json)"
}

for i in 1 2 3 4 5 6; do run_case "base${i}"; done
for i in 1 2 3 4 5 6; do run_case "cap3_${i}" --rtx-max-retries 3; done
echo FREEZE_DONE
