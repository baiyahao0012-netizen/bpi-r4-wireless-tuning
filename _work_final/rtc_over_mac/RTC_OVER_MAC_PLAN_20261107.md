# RTC over MAC：影响分析、仓库资产复用与落地方案

- 日期：2026-11-07
- 复核对象：`bpi-r4-wireless-tuning` 本地克隆 HEAD `1df6285`（= `origin/main`）。GitHub API 返回 404，仓库为私有，故以本地副本为准。
- 场景：STA（笔记本 / Linux）→ AP（BPI-R4，mt7996）**上行**单路 1080p30 高画质视频；AP 有线接算力平台。
- 目标：`RTC over MAC`（去掉 UDP/IP，保留标准 RTC）→ `RTC on MAC`（把截止时间与 QoS 下沉到 MAC）。

---

## 0. 结论（先给判断，后面给证据）

1. **当前项目不是 "over MAC"。** 媒体帧从**有线网口**注入，经 `br-lan` 桥接、由 radio **下行**发出；Wi‑Fi 上的那台机器只做接收。方向、层次、角色三处全和目标场景相反。
2. **当前协议层也不是开源 RTC。** `RTC1`（`0x52544331`）/ `RTC2`（`0x52544332`）都是自研私有头，仓库里没有一处 RTP/RTCP/SRTP。所以"复现开源 RTC 的不受影响功能"在这套协议上无从做起——不是工作量问题，是对象不存在。
3. **去掉 UDP/IP 的直接收益远小于直觉。** 空口上每包只省 28 B（IPv4 20 + UDP 8）；20 Mbps / 1200 B 分片下约 456 kbps，占 2.3%。802.11 的 MAC 头、LLC/SNAP、CCMP、BA、前导两种方案都要有，省不掉。
4. **真正的收益在控制权与可见性。** 能在自己的 AC 队列里排队、能读空口占用与队列深度、能对过期帧说"不重传"——这些是走 UDP/IP 时拿不到的。这也是必须走到 `on MAC` 的原因。
5. **受影响的功能不需要重写 RTC。** 把 L2 做成一个 `net.PacketConn`，标准 RTP/RTCP/SRTP/抖动缓冲/GCC 原样跑通，"不受影响"按构造成立；真正要写代码的是 **7 个适配点**（§3）+ **1 个删除清单**。
6. **Windows 不能当 STA，但不必买树莓派。** 本机双系统 Ubuntu + 现有两块无线网卡即可起步（§5）。

---

## 1. 项目现状复核

### 1.1 实际链路（有代码证据）

| 面 | 实际实现 | 证据位置 | 与目标场景的差距 |
|---|---|---|---|
| 媒体发送 | 绑**以太网口**注入 `0x88B5` 裸帧 | `txport.py:29` `L2Socket(dev_substr=eth_dev, direction=PCAP_D_OUT)`；`DELIVERY` §2.1 发送端 `192.168.240.2` | 方向应为 STA 无线上行 |
| 过空口方式 | 帧进 `br-lan`，由 AP 桥接从 radio 发出 | 同上 + 拓扑图 | 这不是 STA 发送，是 AP 转发 |
| 接收 | Windows + Npcap 在 Wi‑Fi 网卡抓包 | `receiver.py --iface 8812BU` | 接收端应是 AP |
| 反馈 | **有线** Ethernet 回传 | `txport.py:63` `FbTx(dev_substr=eth_dev)` | AP 可原生从空口回，比现在更容易 |
| 码率控制输入 | AP 侧 `iw station dump` 的 **tx** 计数 | `mac_agent.sh:5,12-18` `tx duration / retries / failed` | 上行要换成 RX 侧语义 |
| 协议 | 28 B 私有头 + 帧级分片 + XOR FEC + 自定义 NACK/PLI | `rtc2.py` 全文 | 无 RTP/RTCP/SRTP，不可互通 |
| 连接建立 / 安全 | 静态 MAC；全明文 | `sender.py --dst/--src`；无加密路径 | 无发现、无认证 |

`mac_agent.sh` 里 `IF=phy0.0-ap0`、`STA=40:a5:ef:26:e3:47`，取的是**AP 发往 STA**的 `tx duration`。这行代码本身就说明：整个码率控制闭环建模的是下行。

### 1.2 三个"不是"

- **不是 802.11 MAC。** 代码里没有 802.11 头、ToDS、EDCA/TXOP、A‑MPDU、BA、CCMP。发的是 Ethernet II 帧，802.11 那一层完全由驱动/固件负责。
- **不是双向 RTC。** 单向媒体 + 带外反馈；没有反向媒体、没有会话协商。
- **不是开源协议实现。** 没有 RTP/RTCP/SDP/ICE/DTLS。`webrtc_peer.py` 是 aiortc 对照组，没接进数据通路。

### 1.3 哪些结论成立

| 说法 | 判定 | 依据 |
|---|---|---|
| L2 能承载实时音视频 | 成立 | 干净链路零丢帧、6000+ 帧无错误 |
| FEC/NACK/PLI 有效 | 在私有协议内成立 | 注入 63 分片丢失 → 0 帧丢失 |
| 抖动缓冲 / A/V 同步有效 | 成立（受控条件） | p50 16.7 ms / p95 27.5 ms |
| "RTC 层功能一个没少" | **高估** | 缺 RTP/RTCP/SRTP/SDP/DTLS/ICE |
| "每包省 12 B" | **口径不对** | 见 §2.3：不含 SRTP 才成立；含 SRTP 实际省 22 B，但换来不可互通 + 明文 |
| "MAC 感知 GCC 是核心差异化" | **方向对，证据不足** | `share/attr` 是 AP 下行信号；降码率分支未复测 |

---

## 2. 去掉 UDP/IP 到底去掉了什么

### 2.1 被移除的能力 → 谁在依赖它

| 被移除 | RTC 栈里谁依赖 | 后果 | 结论 |
|---|---|---|---|
| IP 地址 / 子网 / 路由 | SDP `c=` 行、ICE candidate、多宿主 | 协商与候选机制失效 | 需 L2 profile（§3.1） |
| UDP 端口（五元组） | 流分流、RTCP mux 的端口判据 | 音视频 + RTCP 无法靠端口分开 | **可绕过**：`rtcp-mux` 本来就是按 PT(200–223) 判据，天然不依赖端口 |
| UDP 校验和、IP 头校验 | 端到端完整性 | 头被篡改无感知 | SRTP auth tag，或 shim HMAC；链路层已有 CCMP MIC |
| IP 分片 / PMTUD / ICMP "需分片" | 大包透传 | 超 MTU 只能丢，且**没有错误通知** | RTP 打包按 MTU 上限，H.264 用 FU‑A |
| DSCP | QoS 标记 | 无法用 IP 头标优先级 | 802.1p PCP → WMM AC（Linux 用 `SO_PRIORITY`） |
| ECN | 拥塞的显式信号 | GCC 少一个输入 | 退化为 delay gradient + MAC 队列/空口遥测 |
| ICMP / TTL | 快速失败、环路保护 | 二层环路无 TTL 会打爆 | 自建 hop 计数 + 会话超时 |
| NAT / STUN / TURN / ICE | 打洞 | — | **局域网不需要，直接删** |
| IPsec | 逐跳安全 | — | 802.11 CCMP（链路）+ SRTP（端到端，可选） |

### 2.2 完全不受影响、必须原样复用的

编解码（RFC 6184 / 7587）、RTP 打包（RFC 3550）、RTCP SR/RR/SDES/BYE（RFC 3550）、NACK/PLI/FIR（RFC 4585/5104）、RTX（RFC 4588）、ULPFEC/FlexFEC（RFC 8627）、SRTP（RFC 3711）、抖动缓冲、音视频同步、GCC 控制律、pacing、SDP 的 `rtpmap/fmtp/rtcp-mux`。

判断标准只有一条：**这个功能是否直接读写 IP 地址、UDP 端口、NAT、IP 分片、DSCP/ECN、ICMP。** 不读写的，一律不要碰。

### 2.3 头开销：把数算准

| 方案 | MSDU 内字节 | 说明 |
|---|---:|---|
| 标准（RTP+SRTP+UDP+IP） | 12 + 10 + 8 + 20 = **50 B** | SRTP 取 AES‑CM 的 10 B tag；GCM 为 16 B |
| 本方案（RTP+SRTP+shim） | 12 + 10 + 4 = **26 B** | shim：flow_id 1 + hop 1 + flags 1 + 版本 1 |
| 净省 | **24 B** | 不是 28 B，也不是交付文档里的 12 B |

- 1080p30 / 20 Mbps → 1228 B/包 → **2036 pps** → 24 B×2036×8 ≈ **391 kbps ≈ 2.0%**。
- 这 2% 换来的是：不可用 IP 头做 QoS、不可用端口做分流、不可用 ICMP 做诊断。**单看带宽，这笔交易不划算。**

**必须纠正一个直觉：去掉 UDP/IP 不会提高空口效率。** 802.11 的开销（前导、MAC 头、BA、ACK、CCMP、聚合）与 IP/UDP 无关；IP/UDP 只占 28 B，在 1228 B 的包里是 2.3%。想省空口，只能改 MAC 侧（聚合、重传预算、调度），也就是 `on MAC`。

### 2.4 那个真正值钱的收益

| 能力 | 走 UDP/IP | 走 L2 |
|---|---|---|
| 选 AC 队列 | 只能靠 DSCP，且要 AP 侧 nft 改写 | `SO_PRIORITY` 直接落到 `skb->priority` → AC |
| 读本机队列深度 | 只能读 socket 缓冲，失真 | `aql_pending` / qdisc backlog |
| 读空口占用 | 读不到 | AP 侧 per‑STA `airtime`（RX/TX µs，已实测可读） |
| 决定"这个包还值不值得发" | 内核不知道截止时间 | 驱动层可在入队前丢弃过期帧 |
| 包大小上限 | 受 IP MTU + 分片策略约束 | 可到 802.11 MSDU 上限（2304） |

前四条是 `over MAC` 立刻能拿到的，第五条要等 `on MAC`。

---

## 3. 受影响功能的 7 个适配点

写在 L2 适配层里，不碰 RTP 以上任何代码。

| # | 适配点 | 做法 | 验收 |
|---|---|---|---|
| 1 | 编址 | `Addr = {mac(6), flow_id(1)}`；目的 MAC = **AP 本口 MAC 或 br‑lan MAC**，禁止广播；身份用 device_id+PSK，不用 MAC | 两个 STA 不串流 |
| 2 | 分流 | 三个 EtherType 分面（数据 / 反馈 / 控制）；媒体面内用 1 B `flow_id` + **PT 判据**区分 RTP/RTCP | 音视频 + RTCP 不混淆 |
| 3 | MTU / 大帧 | RTP 载荷 ≤ 1200 B；H.264 用 FU‑A；控制报文（SDP/DTLS）应用层分片；重组超时 200 ms | 无超 1500 的帧，无 IP 分片 |
| 4 | 完整性 | SRTP auth tag；shim 内加 hop 计数与版本；禁用 EtherType 白名单外的帧 | 篡改头被拒；环路被 hop 截断 |
| 5 | QoS | `SO_PRIORITY` 6 → AC_VO（反馈）、5 → AC_VI（视频）；AP 侧 EDCA 参数经 beacon 的 WMM IE 下发 | AC 命中率可测 |
| 6 | 发现 / 会话 | 控制 EtherType 上 `hello/offer/ack`（device_id、能力、MTU、SSRC 表）；第一阶段静态表 | 换 IP/换口不用改代码 |
| 7 | 遥测 | AP：per‑STA `airtime`（RX/TX µs）+ `aql_pending` + `survey dump` channel busy；STA：本机 `aql_pending` + 队列 | 1 Hz 稳定采样，不阻塞 |

### 3.1 可以直接删掉的（这是"裁剪"，不是"实现"）

- ICE / STUN / TURN（局域网、AP 已知 STA）
- DTLS‑SRTP 握手（实验室用 PSK 派生 SRTP 主密钥）
- BUNDLE / simulcast / SVC / DataChannel（单路视频起步）
- AEC / AGC / PLC（无音频阶段）
- 浏览器 API、TURN relay、REMB（用 transport‑cc）、RTCP XR 全量

**删除比实现更省事，而且删掉的部分恰好是 WebRTC 里最"IP 依赖"的部分。**

---

## 4. 仓库资产 → 受影响能力的映射（核心回答）

先说总量：核心代码约 **2500 行**（`sender.py` 1044 / `receiver.py` 805 / `rtc2.py` 207 / `txport.py` 228 / `l2sock.py` 143），实验脚本再加约 600 行。其中**协议线格式该淘汰，传输抽象、遥测、算法、测试台该保留**。

| 受影响能力 | 仓库里的对应资产 | 复用度 | 还缺什么 |
|---|---|---|---|
| 编址 / 多流 | `txport.py` 的 transport 抽象（l2/udp 可切换） | ●●●○○ | 无 flow_id、无会话表、MAC 写死 |
| 分面 / 分流 | 三条 EtherType（`0x88B5/6/7`）已经把媒体、反馈、控制分开 | ●●●●○ | 同会话多流无 MID/RID；EtherType 是实验值，出货要换 |
| MTU / 大帧 | `rtc2.chunk_frame(1200)` + `receiver` 的重组与超时（15 ms 兜底） | ●●●○○ | 分片位置错了：应在 RTP/FU‑A，不该在应用层按帧切 |
| 完整性 | 无 | ○○○○○ | SRTP tag 或 shim HMAC |
| 去 NAT/ICE | 无（也不需要） | — | 直接删 |
| **QoS / AC** | `edca_set` 四档实测可设；`_work_merge` 的 mt76 补丁；`mac_agent.sh` 的 AQL/airtime/retry 采集 | ●●●●○ | 方向要翻（下行 tx → 上行 rx）；`SO_PRIORITY→AC` 未验证 |
| **拥塞判据** | `share`（我方空口占比）+ `attr`（视频归因），分离度 8–100 倍 | ●●●●○ | 依赖 `iw station dump`，饱和时阻塞 4–5 s；是 AP 下行语义 |
| 反馈闭环 | `FBK1` 40 B @20 Hz + `Gcc` + `Pacer` | ●●●○○ | 线格式非标准，要换成 RTCP RR + transport‑cc |
| 抖动 / 同步 | `PlayoutClock`/`PlayQueue`（共享播放时钟）+ `SYN1/SYN2` + `clock_ab.py` | ●●●●○ | 时间戳源要换成 RTP / RTCP SR |
| 丢包恢复 | 帧内 XOR + 末片确认 + 15 ms 兜底 + 每缺口只请求一次 | ●●●○○ | 换成 ULPFEC/RTX；1 parity 对 1080p30 够用，对突发不够 |
| **上行遥测** | mac80211 debugfs `stations/<mac>/airtime`（RX/TX µs）、`aql_pending`、`survey dump` | ●●●●○ | 只需换字段语义，**不要重写** |
| 回环 / 抓包 | `l2sock.py`（Windows Npcap，含 `PCAP_D_IN` 方向过滤、非阻塞+事件等待） | ●●●●○ | 仅作 PC 侧抓包；STA 侧要 AF_PACKET |
| 实验台 | `bench*.py` / `sweep_jb*` / `long_run` / `verify_recv` / `an_pcm` | ●●●●○ | 指标要换成整帧完整率、PSNR/VMAF、RTP 级统计 |
| 互通基准 | `webrtc_peer.py`（aiortc） | ●●●●○ | 只做 oracle，不做底座 |

### 4.1 直接复用（不改逻辑）

1. `l2sock.py` 的 Npcap 封装——PC 侧抓包/分析仍在用（方向过滤 `PCAP_D_IN`、非阻塞 + `pcap_getevent` 这套写法是对的）。
2. `mac_agent.sh` 的采集范式——**只需把 `tx packets/bytes/duration/retries/failed` 换成 `rx` 侧字段**，加 `airtime` 与 `survey`，40 行脚本不用重写。
3. 实验脚本与素材（`media/1080p_30fps.mp4` 等 8 个标准素材、`probe_media.py`）。
4. `webrtc_peer.py` 作为行为基线。

### 4.2 改造复用（改接口，不改算法）

1. `PlayoutClock`/`PlayQueue`：`tmin`/`D` 共享时钟的设计是对的，把"帧序号时间轴 + 累计样本数时间轴"换成"RTP 时间戳 + RTCP SR 映射"即可。
2. `Gcc` + `Pacer`：控制律保留，输入从 `FBK1` 换成 RR/transport‑cc；`share/attr` 变成 `CongestionSignalProvider` 的一个实现。
3. `txport.py`：抽象层思路正确，重写成 `DatagramTransport`（见 §4.4），去掉 RTC2 常量。
4. NACK 的四条经验（末片确认、15 ms 兜底、每缺口一次、3 s 缓存）直接搬到 RTX。

### 4.3 淘汰（明确不要再扩展）

`rtc2.py` 的 28 B 头与全部私有语义、`FBK1/NAC1/PLI1/SYN1/SYN2` 报文、按帧分片的 `chunk_idx/chunk_cnt`、16 位 `seq`、32 位 `send_ts_us`。

**为什么必须换掉 16 位 seq：** 1080p30/20 Mbps 下 2036 pps，65536/2036 ≈ **32 秒回绕一次**。300 秒长跑至少回绕 9 次。标准 RTP 有 ROC/扩展序号兜底，RTC2 没有（`DELIVERY` §5 也承认"300 s 循环未复测"）。

### 4.4 目标接口（供实现时对齐）

```text
DatagramTransport
  ReadFrom()  -> (payload, Addr)      # 保留报文边界
  WriteTo(p, Addr)                    # 不重组、不重传、不排序
  LocalAddr() / MTU() -> 1200
  SetPCP(v) / SetAC(ac)               # QoS
  SetReadDeadline(t) / Close()

Addr = { mac: [6]byte, flow_id: uint8 }
```

约束：`WriteTo` 超过 MTU 返回 `ErrMessageTooLong`，由 RTP 层处理；传输层不保证顺序、不重传；任何 `flow_id` 必须能映射到 SSRC/MID，不能只靠 MAC 做身份。

---

## 5. 平台问题：Windows 行不行，要不要树莓派

### 5.1 Windows 为什么当不了 STA（三条硬约束）

1. **没有 802.3 裸发接口。** Windows 的 WLAN 网卡走 NDIS Native 802.11，用户态拿不到"发一个任意 EtherType 的 802.3 帧"的能力；Npcap 在 WLAN miniport 上 `pcap_sendpacket` 不可用。这正是前一个 Agent 把发送端绕到**有线口**的原因——不是设计选择，是被平台逼的。
2. **没有 AC 队列控制。** 没有 `SO_PRIORITY` → `skb->priority` → WMM AC 这条链路，视频帧进不了 AC_VI。
3. **没有 MAC 计数。** 读不到 per‑STA `airtime`、`aql_pending`、`survey channel busy`，`on MAC` 的输入全缺。

结论：**STA 端必须是 Linux。** 但这不等于要买新硬件。

### 5.2 本机现有硬件（实测）

| 网卡 | 型号 | MAC | Linux 驱动 | 用途 |
|---|---|---|---|---|
| 内置无线 | Realtek **8852CE** WiFi 6E PCIe | `C0-35-32-19-CC-FB` | `rtw89`（6.1+ 内置） | M1–M3 主力 STA |
| USB 无线 | MediaTek WiFi 6/6E USB | `90-DE-80-1C-6A-7A` | `mt7921u`（5.16+ 内置） | M4 之后 driver 级实验 |
| 有线 | Realtek PCIe GbE | `40-C2-BA-52-70-95` | `r8169` | 管理 / 抓包 / 导出 |

三块都有原生驱动，**不需要额外买网卡**。

分工理由：8852CE 是 PCIe 2x2 160 MHz，没有 USB 2.0 瓶颈，适合跑吞吐；mt7921u 是 mt76 系，和你已有的 mt7996/EDCA/WDRR 补丁同一套代码风格，适合后面改驱动。

### 5.3 四个方案

| 方案 | 成本 | 优点 | 缺点 | 建议 |
|---|---|---|---|---|
| **A. 笔记本双系统 Ubuntu 24.04** | 0 | 现有硬件全兼容；同一台机器可发可收可分析 | 要切系统；改驱动有风险 | **首选** |
| B. 树莓派 4B + USB 网卡 | ¥500+ | 专用 STA、可随意刷内核/驱动、可无人值守 | 只能当 STA；Pi 5 **没有 H.264 硬编**，别买 5 | 第二阶段再上 |
| C. VMware + USB 无线直通 | 0 | 10 分钟能试 | USB Wi‑Fi 直通不稳、抖动大 | 只做冒烟，不做测量 |
| D. N100 小主机 | ¥700+ | x86 编码强、可长期挂 | 多一台设备 | 需要 7×24 时再考虑 |

**结论：先别买，用 A（Live USB）把链路打通；一旦确定要长期做驱动级实验，再买 N100/N305 迷你主机（选型见 §5.7）。** 理由是那时你会反复重启、反复装模块，拿日常笔记本当试验台的代价太高。

### 5.4 三个必须先解决的坑

1. **MAC 漂移。** 同一台笔记本同时用 Wi‑Fi 和有线接入同一个 `br-lan`，桥会看到"同一主机两个口"，ARP/转发会抖，测量全废。
   → 在 AP 上把有线口独立成 `br-mgmt`（例如 `192.168.241.0/24`），不与 wlan 桥在一起。
2. **目的地址不能用广播。** DA 必须是 AP 本口 MAC（或 br‑lan MAC）。用广播会被 AP 泛洪回空口，自己收两份、时延被污染。
3. **单机回环只收 IN 方向。** 若先用"wlan 发 → AP 桥 → 本机 eth 收"验证，必须 `PCAP_D_IN`/`PACKET_OUTGOING` 过滤，否则发出的副本会污染到达时间（`FEATURE_IMPL_MATRIX` §5.1 已踩过）。

### 5.5 开局五步（第一阶段，无需 AP 侧写代码）

```text
1) Ubuntu 装到外置 USB3 SSD 或独立分区（不动 Windows 分区）
2) 连 AP 的 5 GHz SSID，关省电：iw dev wlan0 set power_save off
3) 确认关联：AP 侧 iw dev phy0.1-ap0 station dump  → 能看到本机 MAC 与 MCS/RSSI
4) 发一个 0x88B5 hello 帧（DA = AP 口 MAC，payload 16 B）
   AP 侧 tcpdump -i br-lan -e ether proto 0x88b5  → 必须看到
5) 若用单机回环：同一帧改成 DA = 本机 eth0 MAC，AP 桥转发，eth0 收到
```

第 4/5 步就是 `over MAC` 的 hello world。**它一旦通，说明"去掉 UDP/IP"在物理上成立**，后面只是把 RTP 塞进这个壳。

### 5.6 能不能不改 Windows？三条真路 + 一条假路

先划清一个边界：**"模拟"不能替代真实空口。** `RTC over MAC` 的全部价值来自 MCS、重传、BA、airtime、channel busy 这些**由真实射频与驱动产生**的量。`mac80211_hwsim` 造虚拟 radio 只能验证协议逻辑（RTP 打包、抖动缓冲、NACK 时序），产不出任何一个可写进报告的数字。所以：

| 路径 | 改不改 Windows | 能否用内置 8852CE | 虚拟化开销 | 能出最终数据 | 判断 |
|---|---|---|---|---|---|
| **A. Live USB 启动 Ubuntu（Try 模式）** | 不分区、不装、不改引导 | ✅ 可用 | 无 | ✅ | **测量首选** |
| **B. VMware + USB 网卡直通** | 不改 | ❌ 只能 USB 网卡 | 有（USB2.0 + VM 调度） | ❌ 只能功能验证 | **可行性首选** |
| C. 双系统 | 改（分区/引导） | ✅ | 无 | ✅ | 长期方案 |
| D. 树莓派/小主机 | 完全不碰 | — | 无 | ✅ | 要改驱动时再上 |
| ✗ WSL2 / Docker / hwsim | 不改 | — | — | ❌ | **不可行**：微软内核不带 cfg80211/mac80211/mt7921u，usbipd 挂进去也无驱动；容器共享宿主内核 |

**本机已核实的前提**

- VMware Workstation **26.0.1** 已安装，`VMnetDHCP`/`VMware NAT Service` 在运行 → B 路径不需要再装软件。
- USB 无线网卡是 **MediaTek MT7921AU**（`USB\VID_0E8D&PID_7961`），**USB 2.0 接口**，实际吞吐 200–300 Mbps 量级；对 20 Mbps 视频不是瓶颈，但 USB 直通会引入额外的调度抖动。
- 内置 8852CE 是 **PCIe**，而 Workstation 在 Windows 上没有 PCIe 直通 → **B 路径用不了内置网卡**，只能用 USB 那块。
- **VBS 正在运行**（`VirtualizationBasedSecurityStatus = 2`）→ Workstation 会跑在 Windows Hypervisor Platform 兼容模式，USB 直通更容易掉设备（attach 后 guest 出现 `mt7921u firmware load failed` / `-EPROTO` 是常见现象）。

**建议的组合（成本与可信度兼顾）**

```text
第 1 步（半天）：VM 里做可行性 —— 只回答"帧能不能从 STA 发出去、AP 能不能收到"
                能通就说明路径成立；不要用它出时延/airtime 结论
第 2 步（当要开始 M2）：切 Live USB 裸机 —— 同一套脚本，零改动，拿真实数据
第 3 步（要改驱动时）：树莓派/小主机，把笔记本彻底摘出试验链路
```

**VM 30 分钟验证清单**

```text
1) 建 Ubuntu 24.04 VM；USB 控制器设 xHCI(USB 3.x)；开启 VT-x/EPT
2) 虚拟机设置里关掉"自动连接新 USB 设备"，启动后手动 attach 0E8D:7961
3) guest: lsusb 见 0e8d:7961；ip link 见 wlan0；iw dev wlan0 scan 有结果
4) 连 AP 的 5G SSID；iw dev wlan0 link 有信号与 MCS
5) 发 16 B 的 0x88B5 帧；AP 侧 tcpdump -i br-lan -e ether proto 0x88b5 收到
```

第 5 步通了就停手，不要继续在 VM 里调时延。USB 直通一旦出现 `-EPROTO` 或设备反复掉线，**直接转 Live USB，不要在直通上耗时间**。

**Live USB 的两个注意点**

- Live 模式默认**不持久化**，重启即清空。做 5 次以上实验时给 U 盘加 persistence，或直接用 USB3 SSD——USB 2.0 普通 U 盘跑 1080p 编码会拖慢启动与写盘。
- 从 U 盘启动不改动 Windows 分区与引导项（UEFI 里一次性选择启动设备），拔掉 U 盘即恢复原状。

> **什么是 Live USB：** 把完整 Linux 写进 U 盘，开机时让固件从 U 盘而不是硬盘引导。系统整体跑在内存里，**不分区、不装引导程序、不写 Windows 盘**，所以关机、拔掉 U 盘、正常开机就是原来的 Windows。它拿到的是**裸机真实内核**（含 `mt7921u`、`mac80211`、真实的 `phy0`），这是虚拟机给不了的东西。制作：8 GB 以上 U 盘 + Ubuntu 24.04 ISO + Rufus（Windows）写入；开机看到厂商 logo 时按 F12 选 U 盘；进菜单选 **Try Ubuntu**，不要选 Install。

### 5.7 外接设备选型

**选型标准（按重要性排序，与"能不能编码"无关）**

| # | 硬要求 | 为什么 | 谁被这条筛掉 |
|---|---|---|---|
| 1 | 完整 Linux（可装内核源码、AF_PACKET、可加载自编模块） | 这是 `over MAC` 的前提，也是 `on MAC` 的唯一入口 | ESP32 / 各类 RTOS 开发板 |
| 2 | 无线网卡可改（在 mac80211 + 开源驱动体系内；**优先 mt76**） | `on MAC` 要改 tx/agg-rx/aql，闭源全卸载驱动碰不到 | 板载 brcmfmac（树莓派自带 Wi‑Fi）、厂商闭源驱动 |
| 3 | 2000 pps 下不抖、不热降频 | 20 Mbps / 1200 B = 2036 pps，抖动会直接进 p95 | 单核小 SoC、无散热的小盒子 |
| 4 | 有线口（管理 / 抓包 / 导出） | 无线只跑媒体，控制必须走另一条路 | 只有 Wi‑Fi 的板子 |
| 5 | 能本地或快速交叉编译内核 | 改一次驱动要等 40 分钟，实验节奏会崩 | 编译慢的 ARM 板 |
| 6 | 可长时间无人值守、不占日常电脑 | 300 s/2 h 长跑是常态 | 拿日常笔记本当试验台 |

> **注意第 1 条的前提：** 第一阶段喂的是 `media/1080p_30fps.mp4`，STA 只需"读文件 → RTP 打包 → 发 2000 pps"，**不需要编码器**。编码能力只有接实时摄像头之后才成为约束。

**候选对比**

| 设备 | 能跑完整 Linux | 无线可改 | 编码（1080p30） | 改驱动迭代 | 约价 | 判断 |
|---|---|---|---|---|---|---|
| ESP32 / ESP32‑S3 / C6 | ❌ | ❌（Espressif 私有 Wi‑Fi 栈，无 mac80211） | ❌ | — | ¥30–80 | **排除** |
| 树莓派 4B（4/8 GB） | ✅ | ✅ 外接 USB 网卡（板载 brcmfmac 不可改） | ⚠️ 硬编存在，但**码率天花板 6–14 Mb/s**（见 5.9） | 模块级重编 1–2 min | ¥550–700 | **排除**（给不出 15–20 Mb/s） |
| 树莓派 5 | ✅ | ✅ 外接 USB 或 PCIe M.2 网卡 | ⚠️ 无硬编；x264 软编 1080p30 @ 20 Mb/s 约 0.9 个单核 | 比 4B 快 | ¥900–1100 | 可用，非首选 |
| **N100 / N305 迷你主机** | ✅ | ✅ 内置 M.2 E‑key 插 MT7922，或 USB | ✅ QSV 硬编，余量极大 | 本机编译最快 | ¥700–1000 | **首选** |
| 旧笔记本（闲置 x86） | ✅ | ✅ | ✅ | ✅ | ¥0 | 有闲置就用 |
| 另一块 OpenWrt 路由器 | ✅ | ✅ mt76 | ❌ 无硬编 | 需整套 SDK | ¥500–1500 | 不建议 |

**结论（明确到可下单）**

- **买：N100 / N305 迷你主机（16 GB / 512 GB，带 2.5G 网口），约 ¥700–1000，装 Ubuntu 24.04。**
- **无线：优先用机身 M.2 2230 E‑key 插槽装 MT7922（`mt7921e`），与 AP 的 MT7996 同属 mt76 体系；机身没有 E‑key 时，用你现有的 MT7921AU（USB 2.0，>50 Mb/s 会先撞 USB）。**
- **不要选 AX210 一类 Intel 网卡**：`iwlwifi` 的速率控制与聚合大量在 Intel 固件里，`on MAC` 改不动。
- **树莓派 4B 排除。** 它不是"CPU 弱"，是**硬编码率天花板**：官方白皮书实测，目标 20 Mb/s 时实际只出 5.95 Mb/s；复杂内容约 6 Mb/s，简单内容至多 14 Mb/s。你要的 15–20 Mb/s 高画质它给不出来。
- **树莓派 5 可用，但不是首选。** 它确实没有硬编，但 x264 软编 1080p30 @ 20 Mb/s 只占 0.9 个单核（低延迟档），画质还比 Pi 4 硬编高 2–3 dB。同价位下 N100 更省事：原生编译、有 E‑key、散热余量大。
- **不买 ESP**：没有 Linux、没有 mac80211，`on MAC` 无从谈起；**ESP‑NOW 不是"RTC over MAC"**，它是私有 L2 帧、吞吐 1 Mbps 量级、无标准 RTP 承载能力。
- **第一阶段喂文件源，不需要编码器。** 上面所有编码差异只在你接摄像头那天之后才成立——所以设备不是开工前提，可以先用 Live USB 把链路跑通再下单。

### 5.8 树莓派 4B 的"编码能力弱"到底指什么

很多人（包括我前一轮）把这句话说得太笼统。它真正的含义是**码率天花板**，不是 CPU 不够。

官方白皮书（*H.264 encoding performance on Raspberry Pi 5-series computers*，RP‑010033‑WP‑1）用 1920×1080、560 帧测试片测得：

| 目标码率 | Pi 4 硬编实出 | Pi 5 软编（低延迟档）实出 | Pi 5 单核占用 |
|---|---|---|---|
| 6.4 Mb/s | 5.89 Mb/s | 6.31 Mb/s | 74% |
| 9.4 Mb/s | 5.94 Mb/s | 9.16 Mb/s | 78% |
| 13.7 Mb/s | 5.95 Mb/s | 13.38 Mb/s | 84% |
| **20 Mb/s** | **5.95 Mb/s（封顶）** | **19.67 Mb/s** | **90%** |

也就是说：**你把目标码率调到 20 Mb/s，它照样只给你 5.95 Mb/s。** 白皮书给出的天花板区间是 6–14 Mb/s，取决于内容复杂度——画面越复杂，封得越低。

其余三条真实短板：

1. **固定功能、无预设**：`h264_v4l2m2m` 背后是 VideoCore 的固定功能编码器，不能调 QP、B 帧、码控策略，只接受一个目标码率。所以"高画质"没法靠调参换来。
2. **没有余量**：1080p30 就是它的上限，参数一动（1080p60、1440p、更高码率）就掉出硬编范围。
3. **热与供电**：持续编码 + USB 网卡同时跑，Pi 4 无散热会在 85 °C 降频；供电不足会掉设备。

对照之下，Pi 5 的软编在同一测试片、同一目标码率下**跑满 20 Mb/s 且只用 0.9 个单核**，PSNR 比 Pi 4 硬编高 2–3 dB。**"Pi 5 只能软编所以更差"这个说法是错的**——对你的 20 Mb/s 目标，能满足的恰恰是 Pi 5，不是 Pi 4。

### 5.9 射频芯片：全 MAC vs 软 MAC（决定"能不能改"）

| 项 | 全 MAC 卸载（brcmfmac、多数 Realtek USB） | 软 MAC 分离（mt76 / ath9k） |
|---|---|---|
| 关联、加密、聚合、BA、速率、重传 | 芯片固件全做 | **host 内核**（mac80211 + mt76）做 |
| host 驱动看到的粒度 | 一个队列，往里塞帧 | 每个 MPDU 的 AC、聚合、重试次数、tx status |
| 你能改的 | 基本没有 | `tx.c` 重试预算、`agg-tx/agg-rx` 窗口、`aql.c` 门限、`mt76_connac` 调度 |
| 固件仍然管的 | 全部 | EDCA 信道接入时序、调制、LDPC、前导 |

所以"mt7921u 只是把帧交给固件"的准确含义是：**mac80211 与 mt76 在 host 侧把 802.11 MPDU 组好、选好 AC、定好重试次数与速率，再交给固件去做时延敏感的射频发送。能被改的正是 host 这一半**——这就是 `on MAC` 的落点。

**为什么是 MT7921 而不是再买一颗 MT7996**

| | MT7996 | MT7921 |
|---|---|---|
| 角色 | AP 芯片（3 频 4x4/2x2） | 客户端芯片（2x2 Wi‑Fi 6/6E） |
| 封装 | PCIe 模块，**无 USB 版本** | USB（MT7921AU）/ PCIe（MT7922） |
| 功耗/散热 | 数瓦，需散热与天线 | 百毫瓦级 |
| 你现在有没有 | **有，就在 BPI‑R4 上** | 有，插在笔记本上 |

买 MT7996 等于再买一颗"AP"，而你要的是"STA"。两者同属 `mt76`/`mt76_connac`，**代码组织是同一套**——所以换 MT7921 不是降级，是换到链路对面的那个角色。

### 5.10 通用性、平移策略与避坑

**什么能搬，什么不能搬**

| 资产 | Pi 4B → Pi 5 | ARM → x86 | 换发行版 |
|---|---|---|---|
| 发送/接收代码（Go/Python、Pion、AF_PACKET、`SO_PRIORITY`） | ✅ 直接跑 | ✅ 重编即可 | ✅ 直接跑 |
| `net.PacketConn` / shim 设计 | ✅ | ✅ | ✅ |
| mac80211 / mt76 **补丁源码** | ✅ 但须按新内核 rebase | ✅ 同样 rebase | ✅ 同样 rebase |
| `.ko` 编译产物 | ❌ 必须重编（vermagic 不同） | ❌ 必须重编 | ❌ 必须重编 |
| USB 网卡 MT7921AU | ✅ 通用 | ✅ 通用 | ✅ 通用 |
| 板载 Wi‑Fi | ❌ 换板即换驱动，Pi 5 仍是 brcmfmac | — | — |
| 编码路径 | ❌ Pi 4 的 `v4l2h264enc` 换成 Pi 5 的 x264 软编（实测 20 Mb/s 够用） | ❌ 换 QSV/NVENC | ❌ 换 |
| 采集/播放脚本 | ⚠️ 改设备名 | ⚠️ 改设备名 | ⚠️ 改设备名 |

**三条策略性结论**

1. **把研究平台锚定在 USB 网卡上，不要锚定在板子上。** MT7921AU 插到树莓派、N100、笔记本上都是同一个 `mt76` 驱动、同一份补丁、同一套代码。换主机时补丁只需按内核版本 rebase，不需要重做 RF/驱动适配。这是最保值的一笔投入。
2. **锁内核。** Ubuntu 上 `apt-mark hold linux-image-* linux-headers-*`，否则一次自动升级就把 rebase 好的补丁打飞，`vermagic` 一变模块直接加载失败。
3. **固件不可改。** MT7921/MT7996 的 Wi‑Fi 固件是闭源的，速率控制、聚合、部分重传在固件里。「on MAC」的边界在 **host driver**，不在 firmware——这也和你 `FEATURE_IMPL_MATRIX` 里 L3「固件不可行」的判断一致。

**避坑**

- 树莓派 4 的 USB 3.0 口对 2.4 GHz 有明显干扰（已知问题）：用 5 GHz，或给网卡加一根 USB 延长线拉远。
- 供电：Pi 4 用官方 5 V/3 A，**Pi 5 必须 5 V/5 A（27 W）**。USB 网卡 + 编码同时跑时，供电不足会周期性掉设备，现象像"驱动崩了"。
- 不需要 monitor 模式注入——你走的是**关联态正常路径**（AF_PACKET + 自定义 EtherType），所以 MT7921AU 在注入上的短板对你不是问题。

### 5.11 STA 端接线与接口分工（树莓派 5 现状）

**结论：能接到 AP 的 5G 上，而且应该用 USB 的 MT7921AU 去接；有线口保留给管理面；板载 Wi‑Fi 关掉。**

```
笔记本 Windows ── eth ──► AP LAN 口 ┐
                                    ├─ br-lan 192.168.240.0/24
树莓派 5 ── eth0 ──────► AP LAN 口 ┘        │
        └─ wlan1 (USB MT7921AU) ── 5G 关联 ──┘
           （媒体面：0x88B5 / RTP 上行，不配 IP）
```

**接口分工（三条硬规则）**

| 接口 | 角色 | IP | 说明 |
|---|---|---|---|
| `eth0` | 管理面 | 有（同 192.168.240.x） | 默认路由、SSH、scp、导出 pcap |
| `wlan1`（MT7921AU） | 媒体面 | **不配 IP** | 只做 AF_PACKET 收发，`SO_BINDTODEVICE` 绑死 |
| 板载 Wi‑Fi | 关闭 | — | `dtoverlay=disable-wifi` |

**为什么不用板载 Wi‑Fi 连 5G**

1. 板载是 `brcmfmac`，全 MAC 卸载，`on MAC` 阶段改不动，连上去也只能当管理链路。
2. 更麻烦的是**同频自干扰**：板载与 USB 都在 5G 时，两块 radio 在同一信道互相争抢，per‑STA `airtime` 里会混进管理流量的空口时间，`share/attr` 判据被污染。
3. 管理面已经有一条有线路径，板载 Wi‑Fi 没有存在必要。

**为什么媒体口不能配 IP**

`eth0` 与 `wlan1` 若同在 `192.168.240.0/24`，内核会有两条到同网段的路由，ARP 会"通量"（谁问都答、从哪个口回不确定），SSH 可能从 `wlan1` 回，媒体帧也可能绕回 `eth0`。媒体口保持无 IP + `SO_BINDTODEVICE`，这两个问题都不存在。

**这条路为什么成立**

关联态 STA 上 `AF_PACKET` 发自定义 EtherType 是可行的：mac80211 把它当普通以太帧，加 **8 B LLC/SNAP** 封进 802.11 数据帧（ToDS=1），AP 收到后由 Linux bridge 按目的 MAC 转发到有线口。所以 `0x88B5` 能从 STA 一路走到 AP 的 `eth`。

两个必须记住的边界：

- 这条路仍是 mac80211 的 data path，**不是** 802.11 MAC 直发。能控制的是 AC、队列、AQL、重传预算——这正是 `over MAC`；`on MAC` 是在这之上再往下改。
- 无线侧还要加 **24–30 B 802.11 头 + 8 B LLC/SNAP + 4 B FCS**。所以"去掉 IP/UDP 省 24 B"只在载荷层成立，空口开销不会因此减少（与 §2.3 结论一致）。

**已核实（2026‑11‑08 只读查询 AP `root@192.168.240.1`）**

| 项 | 实测值 | 结论 |
|---|---|---|
| 5G SSID / 加密 | `BPI-R4-5G` / `psk2`（WPA2‑PSK） | ✅ 兼容，不需要改成 open |
| 5G 信道 / 带宽 | ch149（5745 MHz），80 MHz，`HE80` | ✅ MT7921AU 可关联 |
| 2.4G | `BPI-R4`，ch6，HE20，psk2 | 不建议用于媒体（只 20 MHz） |
| 6G | 已禁用 | 忽略 |
| AP 自身 | 2.4G 作 STA 连上游 `DianGroup103` | 上行出口，与本实验无关 |

**仍需确认的两点**

1. **供电**：Pi 5 必须 5 V/5 A（27 W）。USB 网卡峰值 0.5 A，供电不足会周期性掉 `wlan1`。
2. **USB 口**：插 USB 2.0 口，避开 USB 3.0 的 2.4 GHz 噪声，也不与 NVMe 抢带宽。

**两个容易踩的细节**

1. **目的 MAC 决定谁收到，不是随便填。** `0x88B5` 帧的 dest MAC：
   - 想让**笔记本**收到 → 填笔记本有线口的 MAC（bridge 按转发表转发到那个口）；
   - 想让 **AP 就地收到**（M4 的接收端）→ 填 AP `br-lan` 的 MAC，此时 bridge 交给本机协议栈；
   - 填广播 → bridge 泛洪到所有口，能验证连通但浪费带宽，且会污染空口测量。
   - 填错成 AP 的 Wi‑Fi MAC 而你想让笔记本收，现象是"AP 抓得到、笔记本抓不到"。
2. **接口名不要硬编码。** 内置 Wi‑Fi 通常是 `wlan0`，USB 网卡是 `wlan1`；一旦关掉板载，USB 可能变成 `wlan0`。用 MAC 固定命名（udev 规则或 systemd `.link` 文件），脚本里按名字引用，不按序号。

**笔记本只有一个网口不是问题**

笔记本 `eth` 接 AP 的一个 LAN 口，树莓派 `eth0` 接 AP 的另一个 LAN 口，两者同在 `br-lan`，SSH 直接通。不需要笔记本同时接两台设备。

**唯一要留意的**：媒体帧从 `wlan1` 上行到 AP 后由 bridge 按目的 MAC 转发。若接收端此刻还挂在笔记本上，帧会从 AP 的有线口出来到笔记本——这正是 M1 想要的收包路径；但 `br-lan` 开了 hairpin，要确认 `0x88B5` 不会被反射回同一 radio。

---

## 6. 路线：over MAC → on MAC

| 里程碑 | 内容 | 验收 | 估时 |
|---|---|---|---|
| **M0 冻结** | RTC2 移入 `legacy/`；建 `transport/` `media/` `test/` 骨架；`DatagramTransport` 接口落地 | 旧版本可回退，新目录能跑 hello | 0.5 d |
| **M1 over MAC 打通** | Linux STA → AP 桥 → 本机 eth 收；0x88B5 + 1200 B + 20 Mbps 空载 | pcap 无 IP/UDP；丢包 < 0.01%；p95 时延可测 | 1 d |
| **M2 标准 RTP 视频** | Pion `rtp` + RFC 6184 FU‑A；接收端重组落 `.h264` | Wireshark 按 RTP 正确解析；1080p30 10/15/20 Mbps 各 60 s 可解码 | 2–3 d |
| **M3 反馈与恢复** | RTCP RR/SR + NACK/PLI + RTX + 抖动缓冲 | 注入 0.1% / 突发丢包，整帧完整率 ≥ 95%；p95 ≤ 200 ms | 3–4 d |
| **M4 接收端迁到 AP** | Go 交叉编译 aarch64；AP 落盘 + 统计；有线导出 | AP 连续 10 min 不丢帧、CPU < 30% | 2 d |
| **M5 受影响补丁** | flow_id / 发现 / hop / 完整性 / QoS 五项 | §3 的验收逐条过 | 3–4 d |
| **M6 on MAC** | STA：入队前按截止时间丢弃、AC 映射；AP：ADDBA 响应窗口、WMM EDCA 下发、空口遥测闭环 | 过期帧不占空口；`share/attr` 在上行语义下可用 | 1–2 w |

M1–M3 是"复现不受影响的功能"，M5 是"给受影响的功能打补丁"，M6 才是真正的增量。**顺序不能倒**：M2 之前不要碰 `on MAC`，否则没有可比基线。

---

## 7. 技术选型

| 方案 | 判断 | 理由 |
|---|---|---|
| **Pion（Go）** | **主选** | `rtp`/`rtcp`/`srtp.Context` 都是模块化的，`srtp.Context.EncryptRTP` 是**逐包**接口，天然不绑 UDP；配 `mdlayher/packet` 就能得到一个 `net.PacketConn`；MIT；单二进制交叉编译到 aarch64，AP 端零依赖 |
| GStreamer | 备选 | `rtpbin`/`rtpjitterbuffer`/`rtpulpfec`/`rtx`/`srtp` 现成，但 OpenWrt 上插件集重，还要写 `GstSrc/Sink` |
| aiortc | 只做 oracle | 与现有代码同栈、易对照；传输与 UDP 耦合，性能有限 |
| libwebrtc | 不 fork | 网络层与 ICE/UDP 耦合太深，替换成本高于收益；要浏览器互通就走网关 |

**编码：** STA 侧 `ffmpeg -c:v libx264 -preset ultrafast -tune zerolatency -g 30 -bf 0 -b:v 20M`，或 VAAPI/NVENC 硬编。先跑仓库里的 `media/1080p_30fps.mp4`（可复现），再接摄像头。

---

## 8. 1080p30 的定量边界（用于定参数）

| 码率 | 单帧 | 1200 B 分片 | 无 FEC 整帧丢失（p=0.1%） | 1 parity 后残存 |
|---:|---:|---:|---:|---:|
| 10 Mbps | 41.7 KB | 35 | 3.4% | 0.06% |
| 15 Mbps | 62.5 KB | 53 | 5.2% | 0.14% |
| 20 Mbps | 83.3 KB | 70 | 6.8% | 0.24% |

- 公式：无 FEC `1-(1-p)^N`；1 parity 后 `1-P(0)-P(1)`。
- **随机丢包下 1 个 XOR parity 就够**（20 Mbps 残存 0.24%）；真正致命的是**突发**——MAC 重传耗尽后会整窗丢，XOR 救不回来。所以 FEC 比例要按"突发长度"调，不是按平均丢包率调。
- **空口预算：** 83 KB 一帧在 2.4G/72 Mbps 下约 10 ms，30 fps 就是 **~30% 空口**，余量很薄；5G/600 Mbps 下约 1.2 ms（3.6%）。**首测务必走 5 GHz**，2.4G 只用来验证"拥塞下会不会崩"。
- 若后续降到 15/10 fps 换画质：同码率单帧翻倍，整帧丢失率上升（1080p10/20 Mbps → ~18.8%），**必须同步加强 FEC/ARQ**，"帧率低更稳"是错觉。

---

## 9. 风险与待确认

| # | 项 | 影响 | 需要你确认 |
|---|---|---|---|
| 1 | AP 能否新建 `br-mgmt`（有线独立网段） | 不做就会 MAC 漂移，测量作废 | 改网络配置可能断一次 SSH，能接受吗 |
| 2 | 首测码率 | 决定 FEC 比例与空口余量 | 10 / 15 / 20 Mbps 先跑哪档 |
| 3 | 是否现在并行音频 | 决定 M3 是否要加 RTCP SR 同步 | 先纯视频，还是同步做 |
| 4 | AP 端要不要实时解码 | 决定 AP 的 CPU/存储预算 | 只落盘 + 离线评估，还是要在 AP 上看画面 |
| 5 | `SO_PRIORITY→AC` 与 WMM EDCA 下发是否被驱动采纳 | 影响 QoS 验收 | 只能实测，M1 时顺便验证 |

---

## 10. 一句话

**保留 L2 传输、MAC 遥测、抖动/同步算法和整套实验台；停掉 RTC2；把标准 RTP/RTCP/SRTP 架在一个 `net.PacketConn` 上先跑通，再逐项补 7 个适配点，最后才把截止时间下沉到 MAC。**
现有仓库的价值不在"已经做了什么"，而在**它把 MAC 侧的可观测性打通了**——那恰好是 `on MAC` 唯一不可替代的输入。
