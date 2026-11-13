#!/bin/bash
# debug_t3.sh — 隔离定位 T3 接收链 0 帧问题（本地回环）
set -u
cd /home/bai/rtc_test
CLIP=clip10.mp4
OUT=/tmp/l0
mkdir -p "$OUT"

echo "=== A. 片段帧类型统计 ==="
ffprobe -v error -select_streams v:0 -show_entries frame=pict_type -of csv=p=0 "$CLIP" | sort | uniq -c
echo "=== A2. 前 6 帧类型 ==="
ffprobe -v error -select_streams v:0 -show_entries frame=pict_type -of csv=p=0 "$CLIP" | head -6

run_recv () {
    local name="$1"; local chain="$2"; local port=5014
    rm -f "$OUT/$name.h264"
    pkill -f gst-launch 2>/dev/null; sleep 1
    timeout 20 gst-launch-1.0 -q $chain filesink location="$OUT/$name.h264" 2>"$OUT/$name.recv.err" &
    sleep 1.5
    timeout 12 gst-launch-1.0 -q -e filesrc location="$CLIP" ! qtdemux ! h264parse ! \
        rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=$port \
        2>"$OUT/$name.send.err"
    wait 2>/dev/null
    echo "--- $name ---"
    ls -la "$OUT/$name.h264" 2>/dev/null || echo "no file"
    echo "recv_err:"; cat "$OUT/$name.recv.err"
}

# R1：最简接收链，去掉 jitterbuffer 和 h264parse
run_recv "dbg1" "udpsrc port=5014 ! rtph264depay !"

# R2：加 jitterbuffer，仍不加 h264parse
run_recv "dbg2" "udpsrc port=5014 ! rtpjitterbuffer ! rtph264depay !"

# R3：jitterbuffer + h264parse（复现原 T3 链）
run_recv "dbg3" "udpsrc port=5014 ! rtpjitterbuffer ! rtph264depay ! h264parse !"

echo "=== DONE ==="
