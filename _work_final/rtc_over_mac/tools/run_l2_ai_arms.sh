#!/bin/bash
# Four-arm L2 AI demo: fifo / quota / ai-first / both, with bulk contention.
export LC_ALL=C
DST=40:c2:ba:52:70:95
BASE=0
for mode in fifo quota ai-first both; do
  echo "### $mode"
  echo 12345678 | sudo -S python3 /tmp/l2_ai_client.py \
    --mode "$mode" --dst-mac "$DST" --seconds 10 \
    --rate-mbps 20 --bulk-mbps 40 --flows 4 \
    --ai-interval-ms 100 --qcap 200 --min-per-flow 20 \
    --ack-timeout-ms 50 --max-resend 8 --msg-base "$BASE" \
    --csv "/tmp/l2ai_${mode}.csv" 2>/dev/null | grep -m1 RESULT
  BASE=$((BASE + 100000))
  sleep 1
done
echo L2_AI_DONE
