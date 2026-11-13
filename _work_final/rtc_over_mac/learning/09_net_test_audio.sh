#!/bin/bash
# 09 【历史版本，已撤回，不作基线】音频 Opus RTP 端到端测试
# =========================================================
# ⚠️ 同 08 号脚本：接收端在同一台 Pi 的 netns 里，不构成 STA→AP 基线，仅留管线参考。
#
# 音频链路：AAC 解码 -> Opus 编码 -> RTP -> UDP；接收端 depay -> Opus 解码 -> WAV。
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
RX_WAV=/tmp/rx_audio.wav
RX_LOG=/tmp/net_audio_rx.log
rm -f "$RX_WAV" "$RX_LOG"

echo "===== NETWORK OPUS RTP TEST ====="
echo "sender:   wlan1 192.168.240.126"
echo "receiver: rtc0  192.168.240.154 (netns rtcns)"
echo "path: Pi Wi-Fi -> AP bridge -> Pi Ethernet/macvlan"

# 接收端：UDP 5006 -> 抖动缓冲 -> Opus depay -> Opus 解码 -> 格式转换 -> WAV 落盘
printf '%s\n' '12345678' | sudo -S ip netns exec rtcns \
  timeout 18 gst-launch-1.0 -q \
  udpsrc address=192.168.240.154 port=5006 \
  caps="application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000" \
  ! rtpjitterbuffer latency=100 \
  ! rtpopusdepay ! opusdec ! audioconvert ! audioresample \
  ! audio/x-raw,rate=48000,channels=2 \
  ! wavenc ! filesink location="$RX_WAV" >"$RX_LOG" 2>&1 &
rxpid=$!

sleep 2
echo "receiver pid=$rxpid; sending 10 s of audio..."
t0=$(date +%s)
# 发送端：解出 AAC -> 解码 PCM -> 转换/重采样 -> Opus 编码 -> RTP -> UDP 5006
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample \
  ! opusenc ! rtpopuspay pt=111 \
  ! udpsink host=192.168.240.154 port=5006 bind-address=192.168.240.126 sync=true
send_rc=$?
t1=$(date +%s)
echo "sender_rc=$send_rc elapsed=$((t1-t0))s"

wait "$rxpid" 2>/dev/null || true
echo "rx_wav_size=$(stat -c %s "$RX_WAV" 2>/dev/null || echo 0) bytes"

# 内联 Python：读 WAV 头，打印声道/采样率/帧数/时长。
# 注意：timeout 强杀接收端时 WAV 头可能没回填完整，此时帧数不可信，只能看数据是否写入。
python3 - "$RX_WAV" <<'PY'
import sys, wave, os
p = sys.argv[1]
if not os.path.exists(p) or os.path.getsize(p) < 44:
    print("wav=missing")
    raise SystemExit
w = wave.open(p, 'rb')
print("wav_channels=%d rate=%d frames=%d duration=%.2fs" % (
    w.getnchannels(), w.getframerate(), w.getnframes(),
    w.getnframes() / w.getframerate()))
PY

echo "receiver_log_tail:"
tail -20 "$RX_LOG" 2>/dev/null || true
if [ -s "$RX_WAV" ]; then echo "RESULT=PASS"; else echo "RESULT=FAIL"; fi

# 后续正确测音频同步的做法：
#   用锚点素材（anchor_1080p30_clapper_10s.mkv：每秒白闪帧 + 同刻 50ms 短音），
#   接收端分别检测白帧 PTS 与短音起点 PTS，差值即 A/V 同步偏差；
#   UDP baseline 量一次基准偏差，L2 再量一次，两者相减才是换传输造成的偏差。
