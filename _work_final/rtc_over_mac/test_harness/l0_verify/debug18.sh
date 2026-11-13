#!/bin/bash
# debug18.sh — 音频单路回环定位：接收链 verbose 协商 + opusparse 变体
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
ACAPS="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,pt=111"

run_audio () {
    local name="$1"; local extra="$2"
    pkill -f gst-launch 2>/dev/null; sleep 1
    rm -f "$OUT/$name.pcm"
    timeout 12 gst-launch-1.0 -v -q \
        udpsrc port=5016 caps="$ACAPS" ! queue ! rtpjitterbuffer ! rtpopusdepay ! $extra \
        opusdec ! audioconvert ! audioresample ! \
        audio/x-raw,format=S16LE,channels=1,rate=8000 ! filesink location="$OUT/$name.pcm" \
        2>"$OUT/$name.err" &
    sleep 2
    timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=da \
        da.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
        opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
        2>"$OUT/$name.send.err"
    wait 2>/dev/null
    sz=$(stat -c%s "$OUT/$name.pcm" 2>/dev/null || echo 0)
    echo "$name: pcm_bytes=$sz"
    grep -iE 'caps =|error|could not|not negotiated|no known' "$OUT/$name.err" | head -25
    echo "----"
}

run_audio "a_noparse" ""
run_audio "a_parse" "opusparse !"
