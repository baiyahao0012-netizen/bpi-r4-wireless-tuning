#!/bin/bash
# debug22.sh — T6 闭环：乱序注入 + jitterbuffer 重排验证
# 臂 J：代理成对交换注入乱序，接收端带 jb（期望重排后帧完整、无解码错误）
# 臂 N：同样乱序注入，接收端不带 jb（对照：应出现解码异常/帧缺失）
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
PY=/home/bai/rtc_test/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
PF=86400

run_arm () {
    local tag="$1"; local listen="$2"; local rport="$3"; local use_jb="$4"; local out="$5"
    pkill -f gst-launch 2>/dev/null; pkill -f reorder_proxy 2>/dev/null; sleep 1
    rm -f "$OUT/$out"
    local jb=""
    [ "$use_jb" = "jb" ] && jb="rtpjitterbuffer !"
    timeout 20 gst-launch-1.0 -q \
        udpsrc port="$rport" caps="$VCAPS" ! queue ! $jb rtph264depay ! \
        h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
        video/x-raw,format=I420,width=320,height=180 ! filesink location="$OUT/$out" \
        2>"$OUT/$tag.recv.err" &
    sleep 1.5
    python3 "$PY/reorder_proxy.py" "$listen" 127.0.0.1 "$rport" 12 >"$OUT/$tag.proxy.json" &
    sleep 1
    timeout 12 gst-launch-1.0 -q -e filesrc location=clip10.mp4 ! qtdemux ! h264parse ! \
        rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port="$listen" \
        2>"$OUT/$tag.send.err"
    wait 2>/dev/null
    local sz=$(stat -c%s "$OUT/$out" 2>/dev/null || echo 0)
    local err=$(grep -icE 'error|fail|corrupt|non-existing|missing picture' "$OUT/$tag.recv.err" || true)
    echo "$tag: frames=$((sz/PF)) bytes=$sz recv_err=$err"
    echo "proxy: $(cat "$OUT/$tag.proxy.json")"
}

echo "=== 臂 J：乱序 + jb ==="
run_arm "t6j" 5014 5024 jb "rx_jb.yuv"
echo "=== 臂 N：乱序 + 无 jb（对照）==="
run_arm "t6n" 5015 5025 nojb "rx_nojb.yuv"
