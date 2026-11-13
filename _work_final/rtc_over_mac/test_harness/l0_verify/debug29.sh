#!/bin/bash
# debug29.sh — T7 定向：分叉接收端 RTCP 到探针，确认 NACK(205)/PLI(206) 是否真正发出
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
PY=/home/bai/rtc_test/l0
pkill -f gst-launch 2>/dev/null; pkill -f rtcp_proxy 2>/dev/null; pkill -f loss_proxy 2>/dev/null; sleep 1
rm -f "$OUT/t7g.yuv" "$OUT/t7g.recv.err" "$OUT/t7g.send.err" "$OUT/t7g.rtcp.json"

# 探针：监听 5067 上的接收端 RTCP 反馈
python3 "$PY/rtcp_probe.py" 5067 14 >"$OUT/t7g.rtcp.json" &
sleep 1

GST_DEBUG=3 GST_DEBUG_FILE="$OUT/t7g.recv.err" timeout 22 gst-launch-1.0 rtpbin name=RR do-retransmission=true \
    udpsrc port=5061 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96" ! RR.recv_rtp_sink_0 \
    RR. ! rtph264depay ! h264parse ! avdec_h264 ! \
    videoscale ! videoconvert ! video/x-raw,format=I420,width=320,height=180 ! \
    filesink location="$OUT/t7g.yuv" \
    udpsrc port=5066 ! RR.recv_rtcp_sink_0 \
    RR.send_rtcp_src_0 ! tee name=rt ! queue ! udpsink host=127.0.0.1 port=5065 sync=false async=false \
    rt. ! queue ! udpsink host=127.0.0.1 port=5067 sync=false async=false &
sleep 2

python3 "$PY/loss_proxy.py" 5060 127.0.0.1 5061 20 1 12 >"$OUT/t7g.proxy.json" &
sleep 1

GST_DEBUG=3 GST_DEBUG_FILE="$OUT/t7g.send.err" timeout 12 gst-launch-1.0 -e rtpbin name=RS do-retransmission=true \
    filesrc location=clip10.mp4 ! qtdemux ! h264parse ! rtph264pay pt=96 config-interval=1 ! RS.send_rtp_sink_0 \
    RS.send_rtp_src_0 ! udpsink host=127.0.0.1 port=5060 \
    RS.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5066 sync=false async=false \
    udpsrc port=5065 ! RS.recv_rtcp_sink_0
wait 2>/dev/null

sz=$(stat -c%s "$OUT/t7g.yuv" 2>/dev/null || echo 0)
echo "t7g frames=$((sz/86400)) bytes=$sz"
echo "RTCP 反馈探针: $(cat "$OUT/t7g.rtcp.json")"
echo "proxy: $(cat "$OUT/t7g.proxy.json")"
echo "=== 发送端 NACK/重传 行 ==="
grep -inE 'nack|retrans|history|rtx|feedback' "$OUT/t7g.send.err" | head -15
