#!/bin/bash
# Send H.264 RTP from STA wlan1 to the wired compute platform (laptop .2).
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
DUR=${1:-10}
DST=192.168.240.2

echo "sender: wlan1 192.168.240.126 -> PC $DST:5004"
ROUTE=$(ip route get "$DST" from 192.168.240.126 2>&1)
echo "$ROUTE"
case "$ROUTE" in
  *"dev wlan1"*) ;;
  *) echo "ERROR: media route is NOT via wlan1; refusing to run."; exit 2 ;;
esac

timeout "$DUR" gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host="$DST" port=5004 bind-address=192.168.240.126 sync=true
echo "sender_rc=$?"
