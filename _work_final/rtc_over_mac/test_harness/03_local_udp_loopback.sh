#!/bin/bash
# =============================================================================
# 03_local_udp_loopback.sh — 本机 127.0.0.1 UDP 回环 + RTP 探针
#
# 跑在哪：树莓派 5
# 目的：验证 RTP 包能经 UDP 发出、能被收端按 RTP 头解析；
#       全部走 127.0.0.1，不经过任何真实网络，排除链路变量。
#
# 与 01 的区别：01 用 fakesink 丢弃包；这里真的建 UDP socket 收一遍，
#               由探针解析头字段（包数/序号/SSRC/PT/时间戳）。
#
# 注意：这一步只验证"打包 + UDP 收发 + 头解析"，不做端到端解码；
#       端到端解码在网络测试阶段（05/06）。
# =============================================================================

set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4

# -----------------------------------------------------------------------------
# 视频路：探针监听 5004；rtph264pay 打成 RTP；udpsink 发本机 5004。
#   视频时钟 90 kHz，30 fps 每帧时间戳步长 = 90000/30 = 3000。
# -----------------------------------------------------------------------------
echo "===== VIDEO: localhost UDP loopback ====="
python3 rtp_probe.py 5004 14 > /tmp/vprobe.json 2>/tmp/vprobe.err &
pid=$!
sleep 1
timeout 10 gst-launch-1.0 -q -e \
  filesrc location="$F" \
  ! qtdemux ! h264parse \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=127.0.0.1 port=5004 sync=true
echo "video_udp_rc=$?（124 = timeout 主动结束，预期）"
wait "$pid" 2>/dev/null || true
echo "probe JSON:"
cat /tmp/vprobe.json 2>/dev/null || true
echo

# -----------------------------------------------------------------------------
# 音频路：探针监听 5006；AAC→Opus；rtpopuspay pt=111；发本机 5006。
# -----------------------------------------------------------------------------
echo "===== AUDIO: localhost UDP loopback ====="
python3 rtp_probe.py 5006 10 > /tmp/aprobe.json 2>/tmp/aprobe.err &
pid=$!
sleep 1
timeout 7 gst-launch-1.0 -q -e \
  filesrc location="$F" \
  ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample \
  ! opusenc ! rtpopuspay pt=111 \
  ! udpsink host=127.0.0.1 port=5006 sync=true
echo "audio_udp_rc=$?（124 = timeout 主动结束，预期）"
wait "$pid" 2>/dev/null || true
echo "probe JSON:"
cat /tmp/aprobe.json 2>/dev/null || true

# -----------------------------------------------------------------------------
# 通过标准（本地回环）：
#   - JSON 非空；
#   - ssrcs 只有 1 个；
#   - seq_gaps = 0；
#   - 视频 PT=96，音频 PT=111；
#   - 包数与时长/帧率量级相符（30 fps × 10 s ≈ 300 帧，每帧若干 RTP 包）。
# -----------------------------------------------------------------------------
