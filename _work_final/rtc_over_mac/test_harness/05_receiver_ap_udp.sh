#!/bin/sh
# =============================================================================
# 05_receiver_ap_udp.sh — AP 端接收端（目标版本，尚未跑通）
#
# 跑在哪：BPI-R4 AP（OpenWrt，busybox，GStreamer 1.24.8）
# 目的：在 AP 上终止 RTP：udpsrc → 抖动缓冲 → H.264 depay → 落原始 H.264 文件。
#       解码拿回 Pi/PC 做（AP 上没有 h264parse / avdec_h264，已核实）。
#
# 与被撤回的同机 netns 测试的区别：
#   接收端点在 AP 上，不是同一台 Pi 的另一个网卡/命名空间。
#   这才是 STA→AP 基线要求的接收位置。
#
# AP 环境限制（busybox）：
#   - 无 nohup/setsid/pkill；本脚本前台运行，停止用 `kill <PID>`；
#   - 一次只发一条命令；bash 循环会吞变量，这里全部用 sh 语法。
# =============================================================================

# --- 已核实的 AP 可用插件 -----------------------------------------------------
#   udpsrc              UDP 收包
#   rtpjitterbuffer     抖动缓冲/乱序/重传等待
#   rtph264depay        H.264 RTP 拆包，FU-A 拼回 NAL
#   filesink            落盘
# 缺失：h264parse、avdec_h264（所以不在 AP 上解码）

PORT=5004
OUT=/tmp/rx.h264
LOG=/tmp/rx.log

echo "AP receiver: listen 0.0.0.0:$PORT -> $OUT"
echo "日志: $LOG"

# --- 接收管线 ----------------------------------------------------------------
# udpsrc 上用 caps 点明 RTP 封装，depay 才能正确协商：
#   media=video, encoding-name=H264, payload=96, clock-rate=90000
# rtpjitterbuffer latency=100  给 100 ms 抖动预算（空口到达间隔不均）
# rtph264depay                RTP → H.264 NAL 流
# filesink                    原始 H.264 落盘（不是 MP4，不能直接播放）
#
# 说明：rtph264depay 输出的是裸 H.264 流；取回 Pi/PC 后由 06 脚本接 h264parse
#       再解码计数。落盘文件若缺 SPS/PPS 导致离线解码异常，先核对发送侧
#       config-interval=1 是否在 RTP 里带了配置帧。

gst-launch-1.0 -v \
  udpsrc port=$PORT \
    caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! rtpjitterbuffer latency=100 \
  ! rtph264depay \
  ! filesink location=$OUT \
  2>$LOG

# 管线退出后查看文件大小（busybox stat 用法）：
#   ls -l $OUT
#   wc -c $OUT
#
# 停止接收：另开 SSH 找到 PID 后 kill，不要用 pkill：
#   netstat -ulnp | grep $PORT      # 找 gst-launch PID
#   kill <PID>

# -----------------------------------------------------------------------------
# 后续加音频时（M2 阶段，先不接）：
#   另一路 udpsrc port=5006
#     caps="application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000"
#     ! rtpjitterbuffer
#     ! rtpopusdepay
#     ! filesink location=/tmp/rx.opus
#   RTCP 走独立端口或 rtcp-mux，基线阶段先明文 RTP。
# -----------------------------------------------------------------------------
