# RTC over MAC 测试网络拓扑与多网卡配置

日期：2026-11-08  
适用：Windows 笔记本（单以太网口）+ BPI-R4 AP（OpenWrt，多 LAN 口）+ Raspberry Pi 5（有线接 AP，Wi‑Fi 做 STA 上行）+ 多个同型号 USB Wi‑Fi 网卡。

---

## 1. 结论：不要让笔记本直接连树莓派，用 AP 当交换机

笔记本只有一个网口，不需要同时直连 AP 和树莓派。正确做法是：

```text
                     BPI-R4 AP（OpenWrt）
                    /          |           \
              LAN1(eth)    LAN2(eth)      Wi-Fi AP 5G
                 |             |               |
          Windows 笔记本    树莓派 eth0     树莓派 wlan0
             192.168.240.2  192.168.240.50  无 IP / 仅 raw L2
                    \__________ 同一 br-lan __________/
```

- 笔记本以太网 → AP 的 LAN 口；
- 树莓派以太网 → AP 的另一个 LAN 口；
- 两者在同一 `br-lan`/同一网段，笔记本可以 SSH 树莓派和 AP；
- 树莓派 Wi‑Fi 关联 AP 的 5G SSID，专门跑媒体上行；
- **不要**把笔记本以太网直接插树莓派，否则树莓派同时接 AP 和笔记本，容易形成双路径/环路/ARP 混乱。

---

## 2. IP 规划

沿用现有 `192.168.240.0/24`；如果现场不是这个网段，按实际替换。

| 设备/接口 | IP | 用途 |
|---|---|---|
| AP `br-lan` | `192.168.240.1/24` | 网关、SSH、DHCP |
| Windows 笔记本以太网 | `192.168.240.2/24` | SSH 客户端、管理 |
| 树莓派 `eth0` | `192.168.240.50/24` | SSH、管理、导出 H.264 |
| 树莓派 `wlan0` | **不配 IP**（推荐） | 只发/收 raw L2 媒体帧 |
| 树莓派 `wlan1`（可选） | 不配 IP / 独立网段 | 第二 STA、干扰/监测，基线时关闭 |
| AP Wi‑Fi | 与 `br-lan` 同网段或独立 media VLAN | 接收媒体、回 RTCP |
| DHCP 池 | `192.168.240.100–199` | 动态设备 |
| 静态保留 | `.1` / `.2` / `.50` | AP / 笔记本 / 树莓派 |

> 关键：树莓派 **Wi‑Fi 不配默认路由**。SSH/管理走 `eth0`，媒体 socket 绑定 `wlan0`。这样不会出现“双默认路由/ARP 从 Wi‑Fi 回”的问题。

---

## 3. 两种隔离方案

### 方案 A：简单方案（先做这个）

- AP 的 Wi‑Fi 和 LAN 都在 `br-lan`；
- 树莓派 Wi‑Fi 关联同一个 SSID，但**不配 IP**；
- 媒体帧目的 MAC 用 AP 的 Wi‑Fi MAC（单播），AP 本地收包；
- 管理/SSH 全走以太网；
- 优点：配置最少；缺点：媒体帧可能被桥到 LAN，抓包会看到，但通常不影响。

### 方案 B：媒体 VLAN（更干净，推荐稳定后做）

- AP 新建一个 media SSID/VLAN（如 VLAN 20，`192.168.250.0/24`）；
- 树莓派 Wi‑Fi 接这个 SSID，仍可不配 IP；
- AP 在 media VLAN 上收 raw L2；
- 管理 LAN 与媒体 VLAN 完全隔离，避免环路/广播/抓包污染；
- 需要 OpenWrt 配置 VLAN/bridge，工作量稍大。

**建议：先用 A 打通，再切 B。**

---

## 4. 多网卡策略

### 4.1 树莓派

- **只保留一个媒体 Wi‑Fi 接口**：优先内置 Wi‑Fi；如果内置驱动不支持 raw L2/不稳定，用一只 USB 网卡，并 `ip link set wlan0 down` 关掉内置；
- 其他 USB 网卡基线时**不要插/不要 up**，避免同频竞争、USB 供电和路由混乱；
- 如果以后做多 STA/干扰实验，再启用第二只，并给它单独 MAC/独立网段；
- 多只同型号网卡时，`wlan0/wlan1` 顺序可能变，**按 MAC 固定命名**或用 MAC 选择接口。

### 4.2 Windows 笔记本

- 以太网接 AP LAN，作为 SSH/管理主路径；
- USB Wi‑Fi 基线时全部关闭/不插；它们和树莓派 Wi‑Fi 同频，会干扰测量；
- 如果笔记本需要上网，而 AP 没有 WAN：
  - 用一只 USB Wi‑Fi 连 upstream，默认路由走它；
  - 加一条 `192.168.240.0/24` 走以太网的静态路由；
  - 不要让两块 Wi‑Fi 同时连同一个 AP。
- 后续做“第二 STA/背景流”时，再用第二只 USB 网卡，且不要和媒体 STA 同时跑基线。

### 4.3 接口命名

同型号网卡建议按 MAC 固定：

```bash
ip -br link
# 记录媒体网卡 MAC，例如 00:11:22:33:44:55
```

可选 udev 规则：

```udev
SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="00:11:22:33:44:55", NAME="wlan-rtc"
```

如果不改命名，至少在所有脚本里用 MAC 查找接口，不要硬编码 `wlan0`。

---

## 5. 树莓派 Wi‑Fi 配置（无 IP，仅 raw L2）

### 5.1 关联 AP

用 `wpa_supplicant`：

```bash
sudo ip link set wlan0 up
sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
sudo iw dev wlan0 link
```

`/etc/wpa_supplicant/wpa_supplicant-wlan0.conf`：

```ini
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=CN

network={
    ssid="BPI-R4-5G"
    psk="你的密码"
    key_mgmt=WPA-PSK
}
```

> 如果 AP 用 WPA3，改成 `key_mgmt=SAE`；以实际 AP 配置为准。

### 5.2 不配 IP / 不装默认路由

```bash
sudo ip addr flush dev wlan0
sudo ip link set wlan0 up
ip route show default
ip route get 192.168.240.1   # 应该走 eth0
```

如果使用 NetworkManager，设置：

```bash
nmcli con mod "<wifi-connection>" ipv4.method disabled ipv6.method disabled
nmcli con mod "<wifi-connection>" ipv4.never-default yes ipv6.never-default yes
```

或者把该接口设为 unmanaged，交给 `wpa_supplicant`。

### 5.3 关闭省电

```bash
sudo iw dev wlan0 set power_save off
```

### 5.4 验证 raw L2

```bash
# 树莓派
sudo python3 - <<'PY'
import socket
iface = "wlan0"
dst = bytes.fromhex("AP_MAC".replace(":", ""))
src = bytes.fromhex("PI_WLAN_MAC".replace(":", ""))
s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
s.bind((iface, 0))
s.send(dst + src + b"\x88\xb5" + b"hello-rtc")
PY
```

```bash
# AP
tcpdump -i phy0.1-ap0 -e ether proto 0x88b5
```

AP 能看到，说明媒体通路成立。

---

## 6. AP 侧配置要点

1. 确认 LAN 口都在 `br-lan`：

```bash
brctl show
ip -br addr
```

2. 确认 DHCP 只开在 `br-lan`，LAN 区允许 SSH。
3. Wi‑Fi 用 5GHz，关闭 client isolation，开启 WMM。
4. 媒体目的 MAC 使用 AP 的 Wi‑Fi MAC（单播），不要广播。
5. 抓包：

```bash
tcpdump -i phy0.1-ap0 -e ether proto 0x88b5
# 或
tcpdump -i br-lan -e ether proto 0x88b5
```

6. 若媒体帧被桥到 LAN，且不想让笔记本看到，可在 LAN 口 drop 自定义 EtherType，或改用 media VLAN（方案 B）。

---

## 7. SSH / 远控

拓扑确定后：

```bash
# Windows PowerShell
ssh root@192.168.240.1       # AP
ssh pi@192.168.240.50        # 树莓派以太网
```

- 用 SSH key，不用明文密码；
- 长任务用 `tmux`；
- 树莓派上装：`openssh-server`、`tmux`、`tcpdump`、`iw`、`ethtool`、`ffmpeg`/GStreamer；
- AP 上装：`tcpdump`、`iw`；如需 receiver，交叉编译 Go/C 小工具。

---

## 8. 验证顺序

```text
1. 笔记本 ping AP / 树莓派（以太网）
2. 笔记本 SSH AP / 树莓派
3. 树莓派 wlan0 关联 AP，iw link 正常
4. 树莓派 wlan0 无 IP、无默认路由
5. 树莓派发 0x88B5，AP tcpdump 收到
6. AP 回 0x88B5，树莓派收到
7. 关掉其他 Wi‑Fi 网卡，测 1080p30 RTP
8. 再加音频/多 STA/干扰实验
```

---

## 9. 常见错误

| 错误 | 后果 |
|---|---|
| 笔记本以太网直连树莓派，同时树莓派又接 AP | 双路径/环路/ARP 混乱 |
| 树莓派 Wi‑Fi 也配默认路由 | SSH 可能走 Wi‑Fi，媒体/管理互相干扰 |
| 树莓派 eth0 和 wlan0 同网段都配 IP | ARP flux、回包从错误接口出 |
| 基线时插多只同频 Wi‑Fi 网卡 | 相互竞争，测出来的丢包/时延不可信 |
| 用广播发媒体 | AP 桥泛洪到 LAN，浪费带宽/干扰 |
| 硬编码 `wlan0` | 多网卡顺序变化后脚本发错接口 |
| AP 的 LAN 口插到 WAN 口 | 不在同一 LAN，SSH/媒体都不通 |
