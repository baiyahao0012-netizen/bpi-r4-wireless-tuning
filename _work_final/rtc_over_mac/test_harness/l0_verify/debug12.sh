#!/bin/bash
# debug12.sh — T3 归因第三步：depay 属性清点 + 调试日志查丢弃原因
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"

echo "=== rtph264pay 属性 ==="
gst-inspect-1.0 rtph264pay 2>/dev/null | grep -E '^\s+[a-z-]+' | head -30
echo "=== rtph264depay 属性 ==="
gst-inspect-1.0 rtph264depay 2>/dev/null | grep -E '^\s+[a-z-]+' | head -30

pkill -f gst-launch 2>/dev/null; sleep 1
echo "=== depay 调试日志（fakesink 丢弃输出）==="
GST_DEBUG=rtph264depay:5,rtpjitterbuffer:3 timeout 20 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtph264depay ! fakesink \
    2>"$OUT/depay_debug.err" &
sleep 1.5
timeout 12 gst-launch-1.0 -q -e filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/depay_send.err"
wait 2>/dev/null
echo "=== 丢弃/告警关键词 ==="
grep -iE 'drop|skip|lost|missing|error|warn|discard|buffer' "$OUT/depay_debug.err" | head -30
echo "=== 日志行数 ==="; wc -l "$OUT/depay_debug.err"
