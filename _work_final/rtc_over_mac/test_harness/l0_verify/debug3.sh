#!/bin/bash
# debug3.sh — 定位 fix3.h264 解码告警来源；复测 T5 rtpbin 语法
set -u
cd /home/bai/rtc_test
CLIP=clip10.mp4
OUT=/tmp/l0
mkdir -p "$OUT"

echo "=== 1. 源片段直接解码（基线是否干净） ==="
ffmpeg -i "$CLIP" -an -f null - 2>"$OUT/src_decode.log"
echo "src_decode_rc=$?"
grep -oE 'frame=[ ]*[0-9]+' "$OUT/src_decode.log" | tail -1
echo "src_error_lines=$(grep -icE 'error|missing|non-existing|out of range' "$OUT/src_decode.log")"

echo "=== 2. 源片 ES 提取并扫 NAL ==="
ffmpeg -y -v error -i "$CLIP" -c copy -an "$OUT/src.h264"
python3 /home/bai/rtc_test/l0/nal_scan.py "$OUT/src.h264"
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames \
    -of default=noprint_wrappers=1:nokey=1 "$OUT/src.h264" | sed 's/^/src_h264_frames=/'

echo "=== 3. 接收落盘 fix3.h264 扫 NAL ==="
python3 /home/bai/rtc_test/l0/nal_scan.py "$OUT/fix3.h264"

echo "=== 4. fix3.h264 解码统计 ==="
ffmpeg -i "$OUT/fix3.h264" -an -f null - 2>"$OUT/fix3_decode.log"
echo "fix3_decode_rc=$?"
grep -oE 'frame=[ ]*[0-9]+' "$OUT/fix3_decode.log" | tail -1
echo "fix3_error_lines=$(grep -icE 'error|missing|non-existing|out of range' "$OUT/fix3_decode.log")"
grep -iE 'error|non-existing|out of range|no frame' "$OUT/fix3_decode.log" | head -12

echo "=== 5. T5 rtpbin 语法复测（name 后无点号） ==="
pkill -f gst-launch 2>/dev/null; sleep 1
python3 /home/bai/rtc_test/l0/rtcp_probe.py 5035 16 >"$OUT/t5c.json" 2>"$OUT/t5c.err" &
CP=$!
sleep 1
timeout 14 gst-launch-1.0 -q -e rtpbin name=R \
    filesrc location="$CLIP" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! R.send_rtp_sink \
    R.send_rtp_src ! udpsink host=127.0.0.1 port=5034 \
    R.send_rtcp_src ! udpsink host=127.0.0.1 port=5035 sync=false \
    2>"$OUT/t5c.gst.err"
echo "t5c_rc=$?"
wait "$CP" 2>/dev/null || true
echo "t5c json:"; cat "$OUT/t5c.json"
echo "t5c err:"; cat "$OUT/t5c.gst.err"
echo "=== DONE ==="
