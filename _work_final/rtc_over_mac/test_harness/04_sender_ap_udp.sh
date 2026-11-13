#!/bin/bash
# =============================================================================
# 04_sender_ap_udp.sh — 发送端：Pi wlan1 → AP 192.168.240.1:5004（UDP baseline）
#
# 跑在哪：树莓派 5（STA）
# 目的：把 H.264 RTP 经无线 wlan1 发到 AP，配合 05 脚本在 AP 端落盘。
#
# ⚠️ 路由护栏（本脚本最关键的一段）
# -----------------------------------------------------------------------------
# Pi 上 eth0=.153 和 wlan1=.126 同在 192.168.240.0/24，两条重合直连路由：
#   eth0  metric 100（优先）
#   wlan1 metric 600
# 内核选出口看 metric，不看源 IP。udpsink 的 bind-address=.126 只改源 IP，
# 不改出口网卡——包可能从有线 eth0 溜出去，"无线测试"结论就是假的。
#
# 所以发流前先跑 `ip route get <AP IP> from <wlan1 IP>`：
#   输出必须包含 "dev wlan1"；否则直接拒绝发流（exit 2）。
#
# 修路由的两种办法（二选一，详见 README §7）：
#   A. wlan1 划独立子网 192.168.241.x（最干净，推荐）；
#   B. 策略路由：ip rule add from .126 lookup 100 + 独立表路由；
#      并在 socket 上 SO_BINDTODEVICE 绑 wlan1（udpsink 给不了，需自定义元素）。
# =============================================================================

set -u
cd /home/bai/rtc_test || exit 1

F=1080p30_1_artemis_origins_85s.mp4
DUR=${1:-10}                                   # 发送时长，默认 10 秒，可传参覆盖
AP_IP=192.168.240.1
AP_PORT=5004
WLAN_IP=192.168.240.126

echo "sender: wlan1 $WLAN_IP -> AP $AP_IP:$AP_PORT"

# --- 路由护栏：先查从 wlan1 源地址到 AP 的出口设备 ---------------------------
ROUTE=$(ip route get "$AP_IP" from "$WLAN_IP" 2>&1)
echo "route: $ROUTE"
case "$ROUTE" in
  *"dev wlan1"*) ;;                            # 出口确实是 wlan1，放行
  *) echo "ERROR: media route is NOT via wlan1; refusing to run."; exit 2 ;;
esac

# --- 发送管线 ----------------------------------------------------------------
# filesrc → qtdemux → h264parse → rtph264pay → udpsink
#   config-interval=1  每隔 1 个关键帧带 SPS/PPS（接收端解码需要）
#   pt=96              视频动态载荷类型
#   bind-address=.126  绑定源地址（注意：不改出口网卡，出口由路由决定）
#   sync=true          按时间戳节奏发包，不一口气灌完
#   timeout $DUR       跑满 DUR 秒主动结束（rc=124 是预期，不是失败）
timeout "$DUR" gst-launch-1.0 -q -e filesrc location="$F" \
  ! qtdemux ! h264parse \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host="$AP_IP" port="$AP_PORT" bind-address="$WLAN_IP" sync=true
echo "sender_rc=$?"

# -----------------------------------------------------------------------------
# 发流期间要同时收集的四条硬证据（在另一个终端/AP 上看）：
#   1. Pi:  ip -s link show eth0   TX 增量 ≈ 0
#   2. Pi:  ip -s link show wlan1  TX 增量 ≈ 码率 × 时长
#   3. AP:  tcpdump -i phy0.1-ap0 udp port 5004   抓到来自 .126 的包
#   4. AP:  iw dev phy0.1-ap0 station dump | grep rx bytes   增量对齐 wlan1 TX
# 计数器是开机累计值，必须"先记基线 → 跑 DUR 秒 → 再看增量"，不能直接比绝对值。
# -----------------------------------------------------------------------------
