#!/bin/bash
# env_check.sh — 清点媒体层元件可用性
for e in rtpbin rtpjitterbuffer srtpenc srtpdec rtph264pay rtph264depay \
    rtpopuspay rtpopusdepay opusenc opusdec avdec_h264 h264parse aacparse \
    avdec_aac audioconvert audioresample audiorate identity fakesink filesink \
    udpsrc udpsink qtdemux videoscale videoconvert queue; do
    if gst-inspect-1.0 "$e" >/dev/null 2>&1; then
        echo "$e=yes"
    else
        echo "$e=NO"
    fi
done
echo "--- versions ---"
gst-launch-1.0 --version | head -1
ffmpeg -version | head -1
python3 --version
