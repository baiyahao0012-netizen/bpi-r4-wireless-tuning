#!/bin/bash
# debug25.sh — T7 单臂排障：双 rtpbin 对照，保留完整 GST_DEBUG 日志
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; pkill -f loss_proxy 2>/dev/null; sleep 1
rm -f "$OUT/t7d.yuv" "$OUT/t7d.recv.err" "$OUT/t7d.send.err"

# 接收端 rtpbin（恢复开）
GST_DEBUG=2 GST_DEBUG_FILE="$OUT/t7d.recv.err" timeout 22 gst-launch-1.0 rtpbin name=RR do-retransmission=true \
    udpsrc port=5061 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96" ! RR.recv_rtp_sink_0 \
    RR.recv_rtp_src_0_0_0 ! rtph264depay ! h264parse ! avdec_h264 ! \
    videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180 ! \
    filesink location="$OUT/t7d.yuv" \
    udpsrc port=5066 ! RR.recv_rtcp_sink_0 \
    RR.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5065 sync=false async=false &
sleep 2

# 发送端 rtpbin（无丢失直连 5061）
GST_DEBUG=2 GST_DEBUG_FILE="$OUT/t7d.send.err" timeout 12 gst-launch-1.0 -e rtpbin name=RS do-retransmission=true \
    filesrc location=clip10.mp4 ! qtdemux ! h264parse ! rtph264pay pt=96 config-interval=1 ! RS.send_rtp_sink_0 \
    RS.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5061 \
    RS.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5066 sync=false async=false \
    udpsrc port=5065 ! RS.recv_rtcp_sink_0
wait 2>/dev/null

sz=$(stat -c%s "$OUT/t7d.yuv" 2>/dev/null || echo 0)
echo "t7d bytes=$sz frames=$((sz/86400))"
echo "=== recv.err 关键行 ==="
grep -iE 'error|fail|link|pad|negotiat|cannot|unable|refus|missing|rtpbin|jitter' "$OUT/t7d.recv.err" | head -40
