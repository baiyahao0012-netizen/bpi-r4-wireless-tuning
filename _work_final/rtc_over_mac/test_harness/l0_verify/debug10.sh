#!/bin/bash
# debug10.sh — T3 归因第二步：分段变体定位缺帧发生在哪一级
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
PF=86400

variant () {
    local name="$1"; local chain="$2"
    pkill -f gst-launch 2>/dev/null; sleep 1
    rm -f "$OUT/$name.yuv"
    timeout 20 gst-launch-1.0 -q \
        udpsrc port=5014 caps="$VCAPS" ! $chain ! filesink location="$OUT/$name.yuv" \
        2>"$OUT/$name.err" &
    sleep 1.5
    timeout 12 gst-launch-1.0 -q -e filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
        rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
        2>"$OUT/$name.send.err"
    wait 2>/dev/null
    local sz=$(stat -c%s "$OUT/$name.yuv" 2>/dev/null || echo 0)
    echo "$name: bytes=$sz frames=$((sz/PF)) err=$(grep -icE 'error|fail|corrupt|non-existing' "$OUT/$name.err")"
    grep -iE 'error|non-existing|out of range|no frame' "$OUT/$name.err" | head -4
}

# V1：无 jb、无 parse，depay 直接解码
variant "v1" "queue ! rtph264depay ! avdec_h264 ! videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180"

# V2：加 jitterbuffer
variant "v2" "queue ! rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180"

# V3：完整链（jb + parse）
variant "v3" "queue ! rtpjitterbuffer ! rtph264depay ! h264parse ! avdec_h264 ! videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180"
