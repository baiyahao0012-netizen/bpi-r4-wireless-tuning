#!/bin/bash
# T7 A/B arm runner: arg1 = loss probability, arg2 = seconds
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LOSS=${1:-0.0}
SEC=${2:-20}
NO_RTX=${3:-}
NO_RTX_FLAG=""
if [ "$NO_RTX" = "no-rtx" ]; then NO_RTX_FLAG="--no-rtx"; fi
pkill -f t7_rtx_lab.py 2>/dev/null
sleep 1

python3 /tmp/t7_rtx_lab.py receiver --file /home/bai/rtc_test/clip10.mp4 --host 127.0.0.1 \
  --rtp-port 5004 --rtcp-port 5006 --feedback-port 5005 --loss 0.0 --latency 500 \
  $NO_RTX_FLAG --seconds "$SEC" > /tmp/recv_t7.log 2>&1 &
RPID=$!
sleep 2
python3 /tmp/t7_rtx_lab.py sender --file /home/bai/rtc_test/clip10.mp4 --host 127.0.0.1 \
  --rtp-port 5004 --rtcp-port 5006 --feedback-port 5005 --loss "$LOSS" --latency 500 \
  --seconds "$SEC" > /tmp/send_t7.log 2>&1 &
SPID=$!
wait "$SPID" "$RPID" 2>/dev/null

echo "=== RECEIVER ==="
cat /tmp/recv_t7.log
echo "=== SENDER ==="
cat /tmp/send_t7.log
