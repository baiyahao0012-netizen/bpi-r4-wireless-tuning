#!/bin/bash
# debug13.sh — 验证假设：无 EOS 时解码器尾部 B 帧滞留导致少 2 帧
# 对照：源片含 B 帧（204 B）；派生 -bf 0 无 B 帧片段，走同一条 RTP 回环解码链
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
PF=86400

echo "=== 1. 派生无 B 帧片段（重编码，-bf 0）==="
ffmpeg -y -v error -i clip10.mp4 -c:v libx264 -preset veryfast -bf 0 -keyint 30 -min-keyint 30 -c:a copy "$OUT/clip_nobf.mp4"
NOBF_FRAMES=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1:nokey=1 "$OUT/clip_nobf.mp4")
echo "nobf_frames=$NOBF_FRAMES"

run_loopback () {
    local name="$1"; local clip="$2"
    pkill -f gst-launch 2>/dev/null; sleep 1
    rm -f "$OUT/$name.yuv"
    timeout 20 gst-launch-1.0 -q \
        udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! \
        h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
        video/x-raw,format=I420,width=320,height=180 ! filesink location="$OUT/$name.yuv" \
        2>"$OUT/$name.err" &
    sleep 1.5
    timeout 12 gst-launch-1.0 -q -e filesrc location="$clip" ! qtdemux ! h264parse ! \
        rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
        2>"$OUT/$name.send.err"
    wait 2>/dev/null
    local sz=$(stat -c%s "$OUT/$name.yuv" 2>/dev/null || echo 0)
    echo "$name: bytes=$sz frames=$((sz/PF)) err=$(grep -icE 'error|fail|corrupt|non-existing' "$OUT/$name.err")"
}

echo "=== 2. 原片（含 B 帧）回环 ==="
run_loopback "bf" "clip10.mp4"

echo "=== 3. 无 B 帧片段回环 ==="
run_loopback "nobf" "$OUT/clip_nobf.mp4"
