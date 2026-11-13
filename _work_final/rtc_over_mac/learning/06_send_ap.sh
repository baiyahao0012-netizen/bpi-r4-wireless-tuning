#!/bin/bash
# 06 发送脚本（STA wlan1 -> AP），带路由护栏
# ==============================================
# 为什么需要护栏：
#   Pi 上 eth0(.153) 和 wlan1(.126) 同在 192.168.240.0/24，两条直连路由重叠。
#   内核按 metric 选路：eth0 metric 100 优先，wlan1 metric 600 靠后。
#   udpsink 的 bind-address 只改源 IP，不改出口网卡——媒体可能从有线 eth0 溜出去，
#   那样"无线测试"的结论就是假的。所以发流前先查路由，出口不是 wlan1 就拒绝运行。
#
# 运行：bash 06_send_ap.sh [秒数]   （默认 10 秒）
set -u
cd /home/bai/rtc_test || exit 1
F=1080p30_1_artemis_origins_85s.mp4
DUR=${1:-10}

echo "sender: wlan1 192.168.240.126 -> AP 192.168.240.1:5004"

# 让内核做一次"从 .126 到 AP IP"的路由查询，看走哪块网卡
ROUTE=$(ip route get 192.168.240.1 from 192.168.240.126 2>&1)
echo "$ROUTE"

# 护栏：查询结果里必须包含 "dev wlan1"，否则退出码 2，不发流
case "$ROUTE" in
  *"dev wlan1"*) ;;                                   # 出口是 wlan1，放行
  *) echo "ERROR: media route is NOT via wlan1; refusing to run."; exit 2 ;;
esac

# 发送管线：文件 -> 解封装 -> H.264 规范化 -> RTP 打包 -> UDP 发往 AP:5004
timeout "$DUR" gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.240.1 port=5004 bind-address=192.168.240.126 sync=true

echo "sender_rc=$?"

# 护栏没放行时怎么办（三选一，见 07 号脚本和实现方案 §9.1）：
#   1) 最干净：把 wlan1 划到独立子网 192.168.241.x，与管理面物理隔离；
#   2) 策略路由：ip rule + 独立路由表（07 号脚本）；
#   3) socket 级 SO_BINDTODEVICE 绑网卡（udpsink 的 bind-address 给不了这个）。
#
# 发流后还要用四条硬证据确认走的是无线（见 10 号文档）：
#   eth0 TX 增量≈0；wlan1 TX 增量≈码率×时长；AP 无线口抓到包；station dump rx bytes 对上。
