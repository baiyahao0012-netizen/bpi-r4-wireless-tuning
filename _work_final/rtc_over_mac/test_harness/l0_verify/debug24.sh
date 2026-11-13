#!/bin/bash
# debug24.sh — T7 闭环：丢包注入 + rtpbin NACK/RTX 恢复对照
# 臂 A：无丢失，恢复开启（基线）
# 臂 B：5% 确定性丢失，恢复开启（期望 NACK/RTX 回填，帧完整度接近基线）
# 臂 C：5% 确定性丢失，恢复关闭（对照：应出现丢帧/解码错误）
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
PY=/home/bai/rtc_test/l0
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
PF=86400

run_arm () {
    local tag="$1"; local loss="$2"; local recovery="$3"
    pkill -f gst-launch 2>/dev/null; pkill -f loss_proxy 2>/dev/null; sleep 1
    rm -f "$OUT/$tag.yuv"

    # 接收端 rtpbin
    local rtx="true"; [ "$recovery" = "off" ] && rtx="false"
    timeout 22 gst-launch-1.0 -q rtpbin name=RR do-retransmission=$rtx \
        udpsrc port=5061 ! RR.recv_rtp_sink_0 \
        RR.recv_rtp_src_0_0_0 ! rtph264depay ! h264parse ! avdec_h264 ! \
        videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180 ! \
        filesink location="$OUT/$tag.yuv" \
        udpsrc port=5066 ! RR.recv_rtcp_sink_0 \
        RR.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5065 sync=false async=false \
        2>"$OUT/$tag.recv.err" &
    sleep 2

    if [ "$loss" = "on" ]; then
        python3 "$PY/loss_proxy.py" 5060 127.0.0.1 5061 20 1 12 >"$OUT/$tag.proxy.json" &
        sleep 1
    fi

    # 发送端 rtpbin
    timeout 12 gst-launch-1.0 -q -e rtpbin name=RS do-retransmission=$rtx \
        filesrc location=clip10.mp4 ! qtdemux name=dm ! h264parse ! rtph264pay pt=96 ! RS.send_rtp_sink_0 \
        RS.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5060 \
        RS.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5066 sync=false async=false \
        udpsrc port=5065 ! RS.recv_rtcp_sink_0 \
        2>"$OUT/$tag.send.err"
    wait 2>/dev/null

    local sz=$(stat -c%s "$OUT/$tag.yuv" 2>/dev/null || echo 0)
    local err=$(grep -icE 'error|fail|corrupt|non-existing|missing picture|decode' "$OUT/$tag.recv.err" || true)
    local lost=$(grep -icE 'lost|dropped|nack|retrans' "$OUT/$tag.recv.err" || true)
    echo "$tag: loss=$loss recovery=$recovery frames=$((sz/PF)) bytes=$sz recv_err=$err lost_msgs=$lost"
    [ -f "$OUT/$tag.proxy.json" ] && echo "proxy: $(cat "$OUT/$tag.proxy.json")"
}

echo "=== 臂 A：无丢失 + 恢复开 ==="
run_arm "t7a" off on
echo "=== 臂 B：5% 丢失 + 恢复开 ==="
run_arm "t7b" on on
echo "=== 臂 C：5% 丢失 + 恢复关 ==="
run_arm "t7c" on off
