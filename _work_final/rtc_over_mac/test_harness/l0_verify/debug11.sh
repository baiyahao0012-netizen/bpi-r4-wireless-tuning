#!/bin/bash
# debug11.sh — 对照：不经 RTP，本地同解码/缩放链写 YUV，看链条自身是否丢帧
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; sleep 1

# C1：320x180 缩放链（与 T3 接收链同源元件）
rm -f "$OUT/c1.yuv"
timeout 30 gst-launch-1.0 -q filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=320,height=180 ! filesink location="$OUT/c1.yuv" \
    2>"$OUT/c1.err"
SZ=$(stat -c%s "$OUT/c1.yuv" 2>/dev/null || echo 0)
echo "c1(320x180): bytes=$SZ frames=$((SZ/86400)) err=$(grep -icE 'error|fail|corrupt|non-existing' "$OUT/c1.err")"

# C2：全尺寸不缩放
rm -f "$OUT/c2.yuv"
timeout 30 gst-launch-1.0 -q filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    avdec_h264 ! videoconvert ! \
    video/x-raw,format=I420,width=1920,height=1080 ! filesink location="$OUT/c2.yuv" \
    2>"$OUT/c2.err"
SZ2=$(stat -c%s "$OUT/c2.yuv" 2>/dev/null || echo 0)
PF2=$((1920*1080*3/2))
echo "c2(1920x1080): bytes=$SZ2 frames=$((SZ2/PF2)) err=$(grep -icE 'error|fail|corrupt|non-existing' "$OUT/c2.err")"
grep -iE 'error|non-existing|no frame' "$OUT/c1.err" "$OUT/c2.err" | head -6
