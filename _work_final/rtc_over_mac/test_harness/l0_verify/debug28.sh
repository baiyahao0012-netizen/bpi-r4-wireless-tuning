#!/bin/bash
# debug28.sh — T7 最终三臂对照：丢包注入 + rtpbin NACK/RTX 恢复
# 臂 A：无丢失，恢复开（基线）
# 臂 B：5% 确定性丢失，恢复开（期望 NACK/RTX 回填）
# 臂 C：5% 确定性丢失，恢复关（对照：应出现更多解码错误/缺帧）
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
PY=/home/bai/rtc_test/l0
PF=86400

run_arm () {
    local tag="$1"; local loss="$2"; local recovery="$3"
    pkill -f gst-launch 2>/dev/null; pkill -f loss_proxy 2>/dev/null; sleep 1
    rm -f "$OUT/$tag.yuv" "$OUT/$tag.recv.err" "$OUT/$tag.send.err" "$OUT/$tag.proxy.json"

    local rtx="true"; [ "$recovery" = "off" ] && rtx="false"
    GST_DEBUG=2 GST_DEBUG_FILE="$OUT/$tag.recv.err" timeout 22 gst-launch-1.0 rtpbin name=RR do-retransmission=$rtx \
        udpsrc port=5061 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96" ! RR.recv_rtp_sink_0 \
        RR. ! rtph264depay ! h264parse ! avdec_h264 ! \
        videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180 ! \
        filesink location="$OUT/$tag.yuv" \
        udpsrc port=5066 ! RR.recv_rtcp_sink_0 \
        RR.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5065 sync=false async=false &
    sleep 2

    if [ "$loss" = "on" ]; then
        python3 "$PY/loss_proxy.py" 5060 127.0.0.1 5061 20 1 12 >"$OUT/$tag.proxy.json" &
        sleep 1
    fi

    local rport=5061
    if [ "$loss" = "on" ]; then rport=5060; fi
    GST_DEBUG=2 GST_DEBUG_FILE="$OUT/$tag.send.err" timeout 12 gst-launch-1.0 -e rtpbin name=RS do-retransmission=$rtx \
        filesrc location=clip10.mp4 ! qtdemux ! h264parse ! rtph264pay pt=96 config-interval=1 ! RS.send_rtp_sink_0 \
        RS.send_rtp_src_0 ! udpsink host=127.0.0.1 port=$rport \
        RS.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5066 sync=false async=false \
        udpsrc port=5065 ! RS.recv_rtcp_sink_0
    wait 2>/dev/null

    local sz=$(stat -c%s "$OUT/$tag.yuv" 2>/dev/null || echo 0)
    local err=$(grep -icE 'decode_slice_header|no frame|Invalid input|Failed to send data' "$OUT/$tag.recv.err" || true)
    local lost=$(grep -icE 'packet lost|nack|retrans|rtx' "$OUT/$tag.recv.err" || true)
    echo "$tag: loss=$loss recovery=$recovery frames=$((sz/PF)) bytes=$sz decode_err=$err feedback_msgs=$lost"
    [ -f "$OUT/$tag.proxy.json" ] && echo "proxy: $(cat "$OUT/$tag.proxy.json")"
}

echo "=== 臂 A：无丢失 + 恢复开 ==="
run_arm "t7a" off on
echo "=== 臂 B：5% 丢失 + 恢复开 ==="
run_arm "t7b" on on
echo "=== 臂 C：5% 丢失 + 恢复关 ==="
run_arm "t7c" on off
