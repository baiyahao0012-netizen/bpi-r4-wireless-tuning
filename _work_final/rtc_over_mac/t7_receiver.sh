#!/bin/bash
set -u
rm -f /tmp/t7_rx.yuv
gst-launch-1.0 -v rtpsession name=s rtp-profile=avpf \
  udpsrc port=5000 caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! s.recv_rtp_sink \
  s.recv_rtp_src \
  ! rtprtxreceive payload-type-map="application/x-rtp-pt-map,96=(uint)97" \
  ! rtpjitterbuffer do-retransmission=true do-lost=true latency=500 \
  ! rtph264depay request-keyframe=true ! h264parse ! avdec_h264 \
  ! videoconvert ! videoscale ! video/x-raw,format=I420,width=320,height=180 \
  ! filesink sync=false location=/tmp/t7_rx.yuv \
  s.send_rtcp_src ! udpsink host=127.0.0.1 port=5001 sync=false async=false \
  udpsrc port=5002 ! s.recv_rtcp_sink

