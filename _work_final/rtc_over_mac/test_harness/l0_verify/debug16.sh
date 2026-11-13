#!/bin/bash
# debug16.sh — 隔离发送端：双探针 + 详细协商日志，定位锚点两路为何无 RTP 流出
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
pkill -f gst-launch 2>/dev/null; sleep 1

python3 /home/bai/rtc_test/l0/rtp_probe.py 5014 12 >"$OUT/t16_v.json" 2>"$OUT/t16_v.err" &
python3 /home/bai/rtc_test/l0/rtp_probe.py 5016 12 >"$OUT/t16_a.json" 2>"$OUT/t16_a.err" &
sleep 1
timeout 12 gst-launch-1.0 -v -e filesrc location=anchor.mkv ! matroskademux name=demux \
    demux.video_0 ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    demux.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/t16.send.err"
wait 2>/dev/null
echo "=== 视频探针 ==="; cat "$OUT/t16_v.json"; echo
echo "=== 音频探针 ==="; cat "$OUT/t16_a.json"; echo
echo "=== 协商/链接日志 ==="
grep -iE 'pad|caps|link|error|negotiat|could not|no known' "$OUT/t16.send.err" | head -40
