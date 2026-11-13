#!/bin/bash
# 07 策略路由脚本：把源地址 .126 的流量钉死走 wlan1
# ======================================================
# 背景：默认路由表两条 /24 直连路由重叠，内核可能选 eth0 出口。
# 策略路由（policy routing）做法：
#   - 加一条规则：凡是源 IP = 192.168.240.126 的包，查编号 100 的独立路由表；
#   - 在表 100 里写死：整个 192.168.240.0/24 从 wlan1 出去，源 IP = .126；
#   - 这样即使主表 eth0 metric 更优，.126 的流量也走 wlan1。
#
# 运行（需要 root）：sudo bash 07_setup_media_route.sh
# 撤销（如需）：
#   ip rule del from 192.168.240.126 lookup 100
#   ip route flush table 100
set -e

# 加规则：源 .126 -> 查表 100。已存在则忽略报错（|| true）
ip rule add from 192.168.240.126 lookup 100 2>/dev/null || true

# 表 100 里写死路由：网段走 wlan1，源地址 .126
ip route replace 192.168.240.0/24 dev wlan1 src 192.168.240.126 table 100

echo "rule:"
ip rule show                          # 查看所有策略路由规则
echo "table 100:"
ip route show table 100               # 查看独立路由表内容
echo "route get:"
# 判据：这一行必须显示 dev wlan1；若仍是 dev eth0，说明策略路由没生效
ip route get 192.168.240.1 from 192.168.240.126

# 备注：
# - 独立子网方案（wlan1 用 192.168.241.x）比策略路由更不容易出错，推荐优先；
# - 策略路由只改"从哪个网卡出去"，不改 Wi-Fi 关联、不改 AP 桥接；
# - Pi 的 SSH 管理走 eth0(.153)，不受本脚本影响。
