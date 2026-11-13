#!/bin/bash
set -u
if [ $# -lt 1 ]; then echo "usage: $0 <file>"; exit 2; fi
F="/home/bai/rtc_test/testset_1080p/$1"
if [ ! -f "$F" ]; then echo "missing $F"; exit 2; fi

# Kill any stale shim sender from a previous clip before starting a new one.
sudo -n pkill -f l2_rtp_send.py 2>/dev/null || true
sleep 1

sudo -n python3 /home/bai/rtc_test/l2_rtp_send.py > /tmp/l2_send_${1}.log 2>&1 &
l2pid=$!
trap 'kill $l2pid 2>/dev/null || true' EXIT
sleep 1

timeout 180 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 mtu=1200 \
  ! udpsink host=127.0.0.1 port=5004 sync=true
rc=$?
wait $l2pid 2>/dev/null || true
echo "sender_rc=$rc"
