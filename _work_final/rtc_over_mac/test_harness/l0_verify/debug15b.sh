#!/bin/bash
# debug15b.sh — T8 闭环（双进程版）：视频/音频各自独立 gst-launch，模拟两条独立 RTP 会话
# 臂 A：ffmpeg 直接解码锚点做源基线；臂 B：双路 RTP 本地回环后解码落盘，同脚本分析偏差
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

# ---- 臂 B：双路独立进程 RTP 回环 ----
echo "=== 臂 B：双进程 RTP 回环 ==="
pkill -f gst-launch 2>/dev/null; sleep 1
rm -f "$OUT/rx.yuv" "$OUT/rx.pcm"

# 接收端：视频进程
timeout 22 gst-launch-1.0 -q \
    udpsrc port=5014 caps="$VCAPS" ! queue ! rtpjitterbuffer ! rtph264depay ! \
    h264parse ! avdec_h264 ! videoscale ! videoconvert ! \
    video/x-raw,format=I420,width=$W,height=$H ! filesink location="$OUT/rx.yuv" \
    2>"$OUT/av_recv_v.err" &
# 接收端：音频进程（L0 最小回环无 RTCP 反馈，音频 jb 会滞留缓冲；jb 行为随 M2 rtpbin 闭环复测）
timeout 22 gst-launch-1.0 -q \
    udpsrc port=5016 caps="$ACAPS" ! queue ! rtpopusdepay ! \
    opusdec ! audioconvert ! audioresample ! \
    audio/x-raw,format=S16LE,channels=1,rate=$ARATE ! filesink location="$OUT/rx.pcm" \
    2>"$OUT/av_recv_a.err" &
sleep 2

# 发送端：视频进程
timeout 12 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=dv \
    dv.video_0 ! h264parse ! rtph264pay config-interval=1 pt=96 ! \
    udpsink host=127.0.0.1 port=5014 \
    2>"$OUT/av_send_v.err" &
# 发送端：音频进程
timeout 12 gst-launch-1.0 -q -e filesrc location=anchor.mkv ! matroskademux name=da \
    da.audio_0 ! opusdec ! audioconvert ! audioresample ! audio/x-raw,rate=48000,channels=2 ! \
    opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5016 \
    2>"$OUT/av_send_a.err" &
wait 2>/dev/null

python3 "$PY" --yuv "$OUT/rx.yuv" -W $W -H $H --fps $FPS --pcm "$OUT/rx.pcm" --rate $ARATE >"$OUT/av_rx.json"
cat "$OUT/av_rx.json"; echo
echo "=== 产物大小 ==="
ls -l "$OUT/rx.yuv" "$OUT/rx.pcm"
echo "=== 管线错误行 ==="
grep -icE 'error|fail|corrupt|non-existing' "$OUT"/av_recv_*.err "$OUT"/av_send_*.err || true
