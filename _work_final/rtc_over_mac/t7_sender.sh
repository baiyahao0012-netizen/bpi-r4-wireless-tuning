#!/bin/bash
set -u
gst-launch-1.0 -v rtpsession name=s rtp-profile=avpf \
  filesrc location=/home/bai/rtc_test/clip10.mp4 ! qtdemux name=d d.video_0 ! h264parse \
  ! rtph264pay pt=96 config-interval=1 \
  ! rtprtxsend payload-type-map="application/x-rtp-pt-map,96=(uint)97" \
  ! s.send_rtp_sink \
  s.send_rtp_src ! identity drop-probability=0.001 ! udpsink host=127.0.0.1 port=5000 \
  udpsrc port=5001 ! s.recv_rtcp_sink \
  s.send_rtcp_src ! udpsink host=127.0.0.1 port=5002 sync=false async=false

