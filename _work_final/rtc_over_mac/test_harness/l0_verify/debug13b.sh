#!/bin/bash
# debug13b.sh — 修正 ffmpeg GOP 参数，重跑无 B 帧对照
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
PF=86400

ffmpeg -y -v error -i clip10.mp4 -c:v libx264 -preset veryfast -bf 0 -g 30 -c:a copy "$OUT/clip_nobf.mp4"
NOBF_FRAMES=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of default=noprint_wrappers=1:nokey=1 "$OUT/clip_nobf.mp4")
echo "nobf_frames=$NOBF_FRAMES"

pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/nobf.yuv"
timeout 20 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! \
    h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=320,height=180 ! filesink location="$OUT/nobf.yuv" \
    2>"$OUT/nobf.err" &
sleep 1.5
timeout 12 gst-launch-1.0 -q -e filesrc location="$OUT/clip_nobf.mp4" ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/nobf.send.err"
wait 2>/dev/null
sz=$(stat -c%s "$OUT/nobf.yuv" 2>/dev/null || echo 0)
echo "nobf: bytes=$sz frames=$((sz/PF)) err=$(grep -icE 'error|fail|corrupt|non-existing' "$OUT/nobf.err")"
