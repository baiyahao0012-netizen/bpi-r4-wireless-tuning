#!/bin/bash
# debug9.sh — T3 归因第一步：接收端口探针确认 RTP 是否到齐 302 时间戳
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; sleep 1

echo "=== Run A: 接收端口探针（5014）==="
python3 /home/bai/rtc_test/l0/rtp_probe.py 5014 14 >"$OUT/t3_probe.json" 2>"$OUT/t3_probe.err" &
PP=$!
sleep 1.5
timeout 12 gst-launch-1.0 -q -e filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/t3_probe.send.err"
wait "$PP" 2>/dev/null || true
cat "$OUT/t3_probe.json"
echo
echo "=== 对照：T2 发送侧探针（5004）时间戳应为 302 ==="
