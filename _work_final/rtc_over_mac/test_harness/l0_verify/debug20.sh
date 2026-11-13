#!/bin/bash
# debug20.sh — 音频缓冲流计数：depay/opusdec 调试日志，看包是否进入、是否输出
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
ACAPS="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,pt=111"
pkill -f gst-launch 2>/dev/null; sleep 1

GST_DEBUG=rtpopusdepay:5,opusdec:5 timeout 12 gst-launch-1.0 -q \
    udpsrc port=5016 caps="$ACAPS" ! queue ! rtpopusdepay ! \
    opusdec ! audioconvert ! fakesink \
    2>"$OUT/a20.recv.err" &
sleep 2
timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=da \
    da.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/a20.send.err"
wait 2>/dev/null
echo "recv_log_lines=$(wc -l < "$OUT/a20.recv.err")"
echo "=== depay 关键行 ==="
grep -iE 'receiving|handle|output|drop|skip|lost|error|warn' "$OUT/a20.recv.err" | head -20
echo "=== opusdec 关键行 ==="
grep -iE 'decode|frame|error|warn|missing|header' "$OUT/a20.recv.err" | head -20
echo "=== 尾部 ==="; tail -10 "$OUT/a20.recv.err"
