#!/bin/bash
# debug23.sh — T9 本地 PSNR/SSIM 跑值（仅验证度量流程；本地回环不重编码，近似无损）
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
W=320; H=180; PF=$((W*H*3/2))

# 1) 源参照：不经 RTP 本地解码
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/src9.yuv"
timeout 30 gst-launch-1.0 -q filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=$W,height=$H ! filesink location="$OUT/src9.yuv" \
    2>"$OUT/t9.src.err"
SRC_SZ=$(stat -c%s "$OUT/src9.yuv")
echo "src9 frames=$((SRC_SZ/PF)) bytes=$SRC_SZ"

# 2) 回环解码
rm -f "$OUT/rx9.yuv"
timeout 22 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! \
    h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=$W,height=$H ! filesink location="$OUT/rx9.yuv" \
    2>"$OUT/t9.recv.err" &
RP=$!; sleep 2
timeout 12 gst-launch-1.0 -q -e filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/t9.send.err"
wait "$RP" 2>/dev/null
RX_SZ=$(stat -c%s "$OUT/rx9.yuv")
echo "rx9 frames=$((RX_SZ/PF)) bytes=$RX_SZ"

# 3) PSNR
echo "=== PSNR ==="
ffmpeg -hide_banner -f rawvideo -pix_fmt yuv420p -s ${W}x${H} -i "$OUT/src9.yuv" \
    -f rawvideo -pix_fmt yuv420p -s ${W}x${H} -i "$OUT/rx9.yuv" \
    -filter_complex "[0:v][1:v]psnr=stats_file=$OUT/t9_psnr.log" -f null - 2>&1 | \
    grep -iE 'psnr|average' | tail -5
cat "$OUT/t9_psnr.log" 2>/dev/null | tail -3

# 4) SSIM
echo "=== SSIM ==="
ffmpeg -hide_banner -f rawvideo -pix_fmt yuv420p -s ${W}x${H} -i "$OUT/src9.yuv" \
    -f rawvideo -pix_fmt yuv420p -s ${W}x${H} -i "$OUT/rx9.yuv" \
    -filter_complex "[0:v][1:v]ssim=stats_file=$OUT/t9_ssim.log" -f null - 2>&1 | \
    grep -iE 'ssim|All:' | tail -5
cat "$OUT/t9_ssim.log" 2>/dev/null | tail -3
