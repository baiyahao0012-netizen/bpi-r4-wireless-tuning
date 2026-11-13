#!/bin/bash
# debug19.sh — 最小音频接收链 verbose 诊断（无 -q，保留全部协商输出）
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
ACAPS="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,pt=111"
pkill -f gst-launch 2>/dev/null; sleep 1

timeout 12 gst-launch-1.0 -v \
    udpsrc port=5016 caps="$ACAPS" ! queue ! rtpopusdepay ! \
    opusdec ! audioconvert ! fakesink \
    2>"$OUT/a19.recv.err" &
sleep 2
timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=da \
    da.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/a19.send.err"
wait 2>/dev/null
echo "=== 接收端 stderr 行数 ==="; wc -l "$OUT/a19.recv.err"
echo "=== caps/协商/错误 ==="
grep -iE 'caps =|error|could not|negotiat|no known|missing|refus' "$OUT/a19.recv.err" | head -30
echo "=== 接收端 stderr 尾部 ==="; tail -20 "$OUT/a19.recv.err"
