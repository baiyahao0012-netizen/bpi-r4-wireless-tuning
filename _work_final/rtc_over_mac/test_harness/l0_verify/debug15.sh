#!/bin/bash
# debug15.sh — T8 闭环：锚点素材本地回环音画偏差测量
# 臂 A（源基线）：ffmpeg 直接解码锚点 → YUV + PCM，分析素材自身对齐偏差
# 臂 B（RTP 回环）：视频/音频双路 RTP 本地回环，接收端解码落盘后同脚本分析
set -u
cd /home/bai/rtc_test
OUT=/tmp/l0
PY=/home/bai/rtc_test/l0/av_skew.py
VCAPS="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
ACAPS="application/x-rtp,media=audio,clock-rate=48000,encoding-name=OPUS,pt=111"
W=320; H=180; FPS=30; ARATE=8000

# ---- 臂 A：源基线 ----
echo "=== 臂 A：源素材直接解码 ==="
ffmpeg -y -v error -i anchor.mkv -vf scale=${W}:${H} -pix_fmt yuv420p -f rawvideo "$OUT/src.yuv"
ffmpeg -y -v error -i anchor.mkv -vn -ac 1 -ar $ARATE -f s16le "$OUT/src.pcm"
python3 "$PY" --yuv "$OUT/src.yuv" -W $W -H $H --fps $FPS --pcm "$OUT/src.pcm" --rate $ARATE >"$OUT/av_src.json"
cat "$OUT/av_src.json"; echo

# ---- 臂 B：RTP 双路回环 ----
echo "=== 臂 B：RTP 回环 ==="
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/rx.yuv" "$OUT/rx.pcm"
timeout 22 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! \
    h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=$W,height=$H ! filesink location="$OUT/rx.yuv" \
    udpsrc port=5016 caps="$ACAPS" ! queue ! rtpjitterbuffer ! rtpopusdepay ! \
    opusdec ! audioconvert ! audioresample ! \
    audio/x-raw,format=S16LE,channels=1,rate=$ARATE ! filesink location="$OUT/rx.pcm" \
    2>"$OUT/av_recv.err" &
RP=$!
sleep 2
timeout 12 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=demux \
    demux.video_0 ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5014 \
    demux.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/av_send.err"
wait "$RP" 2>/dev/null || true

python3 "$PY" --yuv "$OUT/rx.yuv" -W $W -H $H --fps $FPS --pcm "$OUT/rx.pcm" --rate $ARATE >"$OUT/av_rx.json"
cat "$OUT/av_rx.json"; echo
echo "=== 管线错误行 ==="
grep -icE 'error|fail|corrupt|non-existing' "$OUT/av_recv.err" "$OUT/av_send.err" || true
