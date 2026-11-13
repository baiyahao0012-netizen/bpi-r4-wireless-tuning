#!/bin/bash
# debug17.sh — 定位：锚点视频单路 / 音频单路 / MP4 转封装 三路隔离
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
probe () { python3 /home/bai/rtc_test/l0/rtp_probe.py "$1" 10; }

echo "=== R1 视频单路（matroskademux）==="
pkill -f gst-launch 2>/dev/null; sleep 1
probe 5014 >"$OUT/t17_v.json" &
PP=$!; sleep 1
timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=d \
    d.video_0 ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/t17_v.err"
wait "$PP" 2>/dev/null; cat "$OUT/t17_v.json"; echo

echo "=== R2 音频单路（matroskademux）==="
pkill -f gst-launch 2>/dev/null; sleep 1
probe 5016 >"$OUT/t17_a.json" &
PP=$!; sleep 1
timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=d \
    d.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/t17_a.err"
wait "$PP" 2>/dev/null; cat "$OUT/t17_a.json"; echo

echo "=== R3 转封装 MP4（视频 copy + 音频 AAC）==="
ffmpeg -y -v error -i anchor.mkv -c:v copy -c:a aac -ac 2 anchor.mp4
ffprobe -v error -show_entries stream=codec_name,codec_type -of csv=p=0 anchor.mp4
pkill -f gst-launch 2>/dev/null; sleep 1
probe 5014 >"$OUT/t17_mp4v.json" &
probe 5016 >"$OUT/t17_mp4a.json" &
PP=$!; sleep 1
timeout 10 gst-launch-1.0 -q -e filesrc location=anchor.mp4 ! qtdemux name=d \
    d.video_0 ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    d.audio_0 ! aacparse ! avdec_aac ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/t17_mp4.err"
wait "$PP" 2>/dev/null
echo "视频:"; cat "$OUT/t17_mp4v.json"; echo
echo "音频:"; cat "$OUT/t17_mp4a.json"; echo
echo "=== 错误行 ==="
grep -icE 'error|fail|corrupt|non-existing' "$OUT/t17_v.err" "$OUT/t17_a.err" "$OUT/t17_mp4.err" || true
