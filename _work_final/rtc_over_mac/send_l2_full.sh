#!/bin/bash
set -u
F=/home/bai/rtc_test/testset_1080p/1080p30_1_artemis_origins_85s.mp4
timeout 180 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 mtu=1200 \
  ! udpsink host=127.0.0.1 port=5004 sync=true
echo "sender_rc=$?"
