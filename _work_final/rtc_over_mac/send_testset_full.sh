#!/bin/bash
# Send one full testset video fromSTA wlan1 to the wired compute platform.
set -u
if [ $# -lt 1 ]; then
  echo "usage: $0 <file.mp4>"
  exit 2
fi
F="/home/bai/rtc_test/testset_1080p/$1"
if [ ! -f "$F" ]; then
  echo "missing: $F"
  exit 2
fi
DST=192.168.240.2
PORT=${2:-5004}
ROUTE=$(ip route get "$DST" from 192.168.240.126 2>&1)
echo "$ROUTE"
case "$ROUTE" in
  *"dev wlan1"*) ;;
  *) echo "ERROR: media route is NOT via wlan1"; exit 2 ;;
esac

echo "sending full: $F"
timeout 180 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host="$DST" port="$PORT" bind-address=192.168.240.126 sync=true
echo "sender_rc=$?"
