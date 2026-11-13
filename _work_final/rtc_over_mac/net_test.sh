#!/bin/bash
# End-to-end RTP over Wi-Fi -> AP bridge -> macvlan receiver on the same Pi.
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
RX_YUV=/tmp/rx_160x90.yuv
RX_LOG=/tmp/net_rx.log
rm -f "$RX_YUV" "$RX_LOG"

echo "===== NETWORK RTP TEST ====="
echo "sender:   wlan1 192.168.240.126"
echo "receiver: rtc0  192.168.240.154 (netns rtcns)"
echo "path: Pi Wi-Fi -> AP bridge -> Pi Ethernet/macvlan"
ip route get 192.168.240.154

# Receiver in the network namespace.  Password is only used for sudo here.
printf '%s\n' '12345678' | sudo -S ip netns exec rtcns \
  timeout 18 gst-launch-1.0 -q \
  udpsrc address=192.168.240.154 port=5004 \
  caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! rtpjitterbuffer latency=100 \
  ! rtph264depay ! h264parse ! avdec_h264 \
  ! videoconvert ! videoscale \
  ! video/x-raw,width=160,height=90,format=I420 \
  ! filesink location="$RX_YUV" >"$RX_LOG" 2>&1 &
rxpid=$!

sleep 2
echo "receiver pid=$rxpid; sending 10 s of video..."
t0=$(date +%s)
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.240.154 port=5004 bind-address=192.168.240.126 sync=true
send_rc=$?
t1=$(date +%s)
echo "sender_rc=$send_rc elapsed=$((t1-t0))s"

wait "$rxpid" 2>/dev/null || true
echo "receiver_rc=$?"
echo "rx_yuv_size=$(stat -c %s "$RX_YUV" 2>/dev/null || echo 0) bytes"
echo "receiver_log_tail:"
tail -20 "$RX_LOG" 2>/dev/null || true

if [ -s "$RX_YUV" ]; then
  echo "RESULT=PASS"
else
  echo "RESULT=FAIL"
fi
