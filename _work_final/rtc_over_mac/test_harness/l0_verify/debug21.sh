#!/bin/bash
# debug21.sh — 音频接收链分段隔离：jb / resample / 声道转换 逐项开关
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
ACAPS="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,pt=111"

run_a () {
    local name="$1"; local chain="$2"
    pkill -f gst-launch 2>/dev/null; sleep 1
    rm -f "$OUT/$name.pcm"
    timeout 12 gst-launch-1.0 -q \
        udpsrc port=5016 caps="$ACAPS" ! $chain ! filesink location="$OUT/$name.pcm" \
        2>"$OUT/$name.err" &
    sleep 2
    timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=da \
        da.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
        opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
        2>"$OUT/$name.send.err"
    wait 2>/dev/null
    local sz=$(stat -c%s "$OUT/$name.pcm" 2>/dev/null || echo 0)
    echo "$name: pcm_bytes=$sz err=$(grep -icE 'error|fail|non-existing' "$OUT/$name.err")"
}

# A：无 jb，48k 立体声直落盘
run_a "aA" "queue ! rtpopusdepay ! opusdec ! audioconvert ! audioresample ! audio/x-raw,format=S16LE,channels=2,rate=48000"
# B：无 jb，重采样到 8k 单声道
run_a "aB" "queue ! rtpopusdepay ! opusdec ! audioconvert ! audioresample ! audio/x-raw,format=S16LE,channels=1,rate=8000"
# C：带 jb，48k 立体声直落盘
run_a "aC" "queue ! rtpjitterbuffer ! rtpopusdepay ! opusdec ! audioconvert ! audioresample ! audio/x-raw,format=S16LE,channels=2,rate=48000"
