#!/bin/bash
# debug27.sh — T7 排障 v3：接收输出侧用裸 rtpbin. 动态挂接（官方示例写法）
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/t7f.yuv" "$OUT/t7f.recv.err" "$OUT/t7f.send.err"

GST_DEBUG=2 GST_DEBUG_FILE="$OUT/t7f.recv.err" timeout 22 gst-launch-1.0 rtpbin name=RR do-retransmission=true \
    udpsrc port=5061 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96" ! RR.recv_rtp_sink_0 \
    RR. ! rtph264depay ! h264parse ! avdec_h264 ! \
    videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180 ! \
    filesink location="$OUT/t7f.yuv" \
    udpsrc port=5066 ! RR.recv_rtcp_sink_0 \
    RR.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5065 sync=false async=false &
sleep 2

GST_DEBUG=2 GST_DEBUG_FILE="$OUT/t7f.send.err" timeout 12 gst-launch-1.0 -e rtpbin name=RS do-retransmission=true \
    filesrc location=clip10.mp4 ! qtdemux ! h264parse ! rtph264pay pt=96 config-interval=1 ! RS.send_rtp_sink_0 \
    RS.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5061 \
    RS.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5066 sync=false async=false \
    udpsrc port=5065 ! RS.recv_rtcp_sink_0
wait 2>/dev/null

sz=$(stat -c%s "$OUT/t7f.yuv" 2>/dev/null || echo 0)
echo "t7f bytes=$sz frames=$((sz/86400))"
echo "=== recv not-linked/error ==="
grep -iE 'not-linked|error|无法|失败' "$OUT/t7f.recv.err" | head -20
echo "=== send not-linked/error ==="
grep -iE 'not-linked|error|无法|失败' "$OUT/t7f.send.err" | head -20
