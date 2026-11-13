#!/bin/bash
# debug6.sh — T3 帧级闭环：接收端解码后降采样写原始 YUV，按每帧字节数反算帧数
set -u
cd /home/bai/rtc_test
CLIP=clip10.mp4
OUT=/tmp/l0
mkdir -p "$OUT"
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"

W=320; H=180
PER=$((W*H*3/2))

echo "=== 0. 源片分辨率 ==="
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$CLIP"

echo "=== 1. 接收端解码 + YUV 落盘（320x180 I420） ==="
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/rx.yuv"
timeout 20 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! rtpjitterbuffer ! rtph264depay ! h264parse ! \
    avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=$W,height=$H ! filesink location="$OUT/rx.yuv" \
    2>"$OUT/t3f.recv.err" &
RP=$!
sleep 1.5
timeout 12 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/t3f.send.err"
T3F_SEND_RC=$?
wait "$RP" 2>/dev/null; T3F_RECV_RC=$?
echo "send_rc=$T3F_SEND_RC recv_rc=$T3F_RECV_RC"

SZ=$(stat -c%s "$OUT/rx.yuv" 2>/dev/null || echo 0)
FRAMES=$((SZ / PER))
echo "yuv_bytes=$SZ per_frame=$PER decoded_frames=$FRAMES"
echo "recv_err_lines=$(grep -icE 'error|fail|corrupt|wrong|non-existing' "$OUT/t3f.recv.err")"
echo "=== recv err ==="; cat "$OUT/t3f.recv.err"
echo "=== send err ==="; cat "$OUT/t3f.send.err"
echo "=== DONE ==="
