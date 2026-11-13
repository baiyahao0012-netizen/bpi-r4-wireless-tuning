#!/bin/bash
# Send H.264 RTP from STA wlan1 to AP, with a route guard.
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
DUR=${1:-10}

echo "sender: wlan1 192.168.240.126 -> AP 192.168.240.1:5004"
ROUTE=$(ip route get 192.168.240.1 from 192.168.240.126 2>&1)
echo "$ROUTE"
case "$ROUTE" in
  *"dev wlan1"*) ;;
  *) echo "ERROR: media route is NOT via wlan1; refusing to run."; exit 2 ;;
esac

timeout "$DUR" gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.240.1 port=5004 bind-address=192.168.240.126 sync=true
echo "sender_rc=$?"
