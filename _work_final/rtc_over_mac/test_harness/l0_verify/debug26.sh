#!/bin/bash
# debug26.sh — T7 排障 v2：RTCP udpsrc 补 application/x-rtcp caps，单臂对照
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/t7e.yuv" "$OUT/t7e.recv.err" "$OUT/t7e.send.err"

GST_DEBUG=2 GST_DEBUG_FILE="$OUT/t7e.recv.err" timeout 22 gst-launch-1.0 rtpbin name=RR do-retransmission=true \
    udpsrc port=5061 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96" ! RR.recv_rtp_sink_0 \
    RR.recv_rtp_src_0_0_0 ! rtph264depay ! h264parse ! avdec_h264 ! \
    videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180 ! \
    filesink location="$OUT/t7e.yuv" \
    udpsrc port=5066 caps="application/x-rtcp" ! RR.recv_rtcp_sink_0 \
    RR.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5065 sync=false async=false &
sleep 2

GST_DEBUG=2 GST_DEBUG_FILE="$OUT/t7e.send.err" timeout 12 gst-launch-1.0 -e rtpbin name=RS do-retransmission=true \
    filesrc location=clip10.mp4 ! qtdemux ! h264parse ! rtph264pay pt=96 config-interval=1 ! RS.send_rtp_sink_0 \
    RS.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5061 \
    RS.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5066 sync=false async=false \
    udpsrc port=5065 caps="application/x-rtcp" ! RS.recv_rtcp_sink_0
wait 2>/dev/null

sz=$(stat -c%s "$OUT/t7e.yuv" 2>/dev/null || echo 0)
echo "t7e bytes=$sz frames=$((sz/86400))"
echo "=== recv not-linked/error ==="
grep -iE 'not-linked|error|无法|失败' "$OUT/t7e.recv.err" | head -20
echo "=== send not-linked/error ==="
grep -iE 'not-linked|error|无法|失败' "$OUT/t7e.send.err" | head -20
