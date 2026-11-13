#!/bin/bash
# debug5.sh — T3：AVCC 落盘离线转 annexb 后帧对账；T5 探针 PT 取整字节复测
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0

echo "=== 1. fix3 AVCC -> annexb (mp4toannexb) ==="
ffmpeg -y -v error -i "$OUT/fix3.h264" -c copy -bsf:v h264_mp4toannexb "$OUT/fix3_axb.h264" 2>"$OUT/fix3_bsf.err"
echo "bsf_rc=$?"
ls -la "$OUT/fix3_axb.h264"
od -A x -t x1z "$OUT/fix3_axb.h264" | head -3
python3 /home/bai/rtc_test/l0/nal_scan.py "$OUT/fix3_axb.h264"
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames \
    -of default=noprint_wrappers=1:nokey=1 "$OUT/fix3_axb.h264" | sed 's/^/axb_frames=/'
ffmpeg -i "$OUT/fix3_axb.h264" -an -f null - 2>"$OUT/fix3_axb_decode.log"
echo "axb_decode_rc=$?"
grep -oE 'frame=[ ]*[0-9]+' "$OUT/fix3_axb_decode.log" | tail -1
echo "axb_error_lines=$(grep -icE 'error|non-existing|out of range|no frame' "$OUT/fix3_axb_decode.log")"
grep -iE 'error|non-existing|out of range|no frame' "$OUT/fix3_axb_decode.log" | head -8
echo "bsf err:"; cat "$OUT/fix3_bsf.err"

echo "=== 2. T5 复测（探针已改整字节 PT） ==="
pkill -f gst-launch 2>/dev/null; sleep 1
python3 /home/bai/rtc_test/l0/rtcp_probe.py 5035 16 >"$OUT/t5e.json" 2>"$OUT/t5e.err" &
CP=$!
sleep 1
timeout 14 gst-launch-1.0 -q -e rtpbin name=R \
    filesrc location=clip10.mp4 ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! R.send_rtp_sink_0 \
    R.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5034 \
    R.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5035 sync=false async=false \
    2>"$OUT/t5e.gst.err"
echo "t5e_rc=$?"
wait "$CP" 2>/dev/null || true
echo "t5e json:"; cat "$OUT/t5e.json"
echo "t5e err:"; cat "$OUT/t5e.gst.err"
echo "=== DONE ==="
