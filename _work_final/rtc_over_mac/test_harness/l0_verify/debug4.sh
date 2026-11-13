#!/bin/bash
# debug4.sh — T3 annexb 落盘对账；T5 rtpbin 带序号面板复测
set -u
cd /home/bai/rtc_test
CLIP=clip10.mp4
OUT=/tmp/l0
mkdir -p "$OUT"
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"

echo "=== 0. 既有文件头字节对比 ==="
for f in fix1 fix2 fix3; do
    echo "--- $f ---"; od -A x -t x1z "$OUT/$f.h264" 2>/dev/null | head -2
done

echo "=== 1. fix4：强制 annexb 落盘 ==="
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/fix4.h264"
timeout 20 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! rtpjitterbuffer ! rtph264depay ! h264parse ! \
    video/x-h264,stream-format=annexb,alignment=au ! filesink location="$OUT/fix4.h264" \
    2>"$OUT/fix4.recv.err" &
sleep 1.5
timeout 12 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! h264parse ! \
    rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/fix4.send.err"
wait 2>/dev/null
echo "fix4 size:"; ls -la "$OUT/fix4.h264"
echo "fix4 head:"; od -A x -t x1z "$OUT/fix4.h264" | head -3
python3 /home/bai/rtc_test/l0/nal_scan.py "$OUT/fix4.h264"
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames \
    -of default=noprint_wrappers=1:nokey=1 "$OUT/fix4.h264" | sed 's/^/fix4_frames=/'
ffmpeg -i "$OUT/fix4.h264" -an -f null - 2>"$OUT/fix4_decode.log"
echo "fix4_decode_rc=$?"
grep -oE 'frame=[ ]*[0-9]+' "$OUT/fix4_decode.log" | tail -1
echo "fix4_error_lines=$(grep -icE 'error|non-existing|out of range|no frame' "$OUT/fix4_decode.log")"
echo "fix4 recv_err:"; cat "$OUT/fix4.recv.err"

echo "=== 2. T5 rtpbin 带 _0 面板复测 ==="
pkill -f gst-launch 2>/dev/null; sleep 1
python3 /home/bai/rtc_test/l0/rtcp_probe.py 5035 16 >"$OUT/t5d.json" 2>"$OUT/t5d.err" &
CP=$!
sleep 1
timeout 14 gst-launch-1.0 -q -e rtpbin name=R \
    filesrc location="$CLIP" ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 ! R.send_rtp_sink_0 \
    R.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5034 \
    R.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5035 sync=false async=false \
    2>"$OUT/t5d.gst.err"
echo "t5d_rc=$?"
wait "$CP" 2>/dev/null || true
echo "t5d json:"; cat "$OUT/t5d.json"
echo "t5d err:"; cat "$OUT/t5d.gst.err"
echo "=== DONE ==="
