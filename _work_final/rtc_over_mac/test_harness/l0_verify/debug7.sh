#!/bin/bash
# debug7.sh — T3 预热/queue 复测，确认缺 2 帧是否启动竞态
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"

pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/rx2.yuv"
timeout 22 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! h264parse ! \
    avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=320,height=180 ! filesink location="$OUT/rx2.yuv" \
    2>"$OUT/t3f2.recv.err" &
sleep 3
timeout 12 gst-launch-1.0 -q -e filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/t3f2.send.err"
wait 2>/dev/null
SZ=$(stat -c%s "$OUT/rx2.yuv" 2>/dev/null || echo 0)
echo "bytes=$SZ frames=$((SZ/86400))"
echo "recv_err=$(grep -icE 'error|fail|corrupt|wrong|non-existing' "$OUT/t3f2.recv.err")"
echo "=== recv err ==="; cat "$OUT/t3f2.recv.err"
echo "=== send err ==="; cat "$OUT/t3f2.send.err"
