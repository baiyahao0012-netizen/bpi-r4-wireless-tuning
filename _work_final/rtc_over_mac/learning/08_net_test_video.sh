#!/bin/bash
# 08 【历史版本，已撤回，不作基线】视频端到端测试
# =====================================================
# ⚠️ 为什么撤回：
#   接收端是同一台 Pi 上的 netns/macvlan（192.168.240.154），不是 AP 端点。
#   包裹从 Pi 出门、绕 AP 桥一圈，又回到 Pi 自己的另一个虚拟口。
#   这只能证明"媒体层 + 真实 Wi-Fi/桥链路可用"，不能作为 STA→AP 基线。
#   临时 netns/macvlan/路由已删除，本脚本仅留作"接收端管线写法"参考。
#
# 正确的 STA→AP 基线应是：
#   Pi wlan1 .126 -> AP .1:5004 -> AP 上 udpsrc/jitterbuffer/depay -> 落盘
#   （或 AP 后面的有线参考接收端，且明确标注为 reference receiver）
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
RX_YUV=/tmp/rx_160x90.yuv
RX_LOG=/tmp/net_rx.log
rm -f "$RX_YUV" "$RX_LOG"

echo "===== NETWORK RTP TEST ====="
echo "sender:   wlan1 192.168.240.126"
echo "receiver: rtc0  192.168.240.154 (netns rtcns)"
echo "path: Pi Wi-Fi -> AP bridge -> Pi Ethernet/macvlan"
ip route get 192.168.240.154          # 发流前先看出口（和 06 号脚本同样的护栏思路）

# 在 netns 里起接收端：UDP 收包 -> 抖动缓冲 -> H.264 解封装 -> 解析 -> 软解 -> 缩到 160x90 -> 落 YUV
# sudo 密码仅用于本机提权进 netns，不进 git
printf '%s\n' '12345678' | sudo -S ip netns exec rtcns \
  timeout 18 gst-launch-1.0 -q \
  udpsrc address=192.168.240.154 port=5004 \
  caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! rtpjitterbuffer latency=100 \
  ! rtph264depay ! h264parse ! avdec_h264 \
  ! videoconvert ! videoscale \
  ! video/x-raw,width=160,height=90,format=I420 \
  ! filesink location="$RX_YUV" >"$RX_LOG" 2>&1 &
rxpid=$!

sleep 2                                # 等接收端绑定端口
echo "receiver pid=$rxpid; sending 10 s of video..."
t0=$(date +%s)
timeout 10 gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.240.154 port=5004 bind-address=192.168.240.126 sync=true
send_rc=$?
t1=$(date +%s)
echo "sender_rc=$send_rc elapsed=$((t1-t0))s"

wait "$rxpid" 2>/dev/null || true
echo "receiver_rc=$?"
# 帧数反推：160x90 I420 每帧 21600 字节；文件大小 / 21600 = 帧数
echo "rx_yuv_size=$(stat -c %s "$RX_YUV" 2>/dev/null || echo 0) bytes"
echo "receiver_log_tail:"
tail -20 "$RX_LOG" 2>/dev/null || true

# 判定只看"有没有落文件"；帧完整率要对照源帧数另算
if [ -s "$RX_YUV" ]; then
  echo "RESULT=PASS"
else
  echo "RESULT=FAIL"
fi
