# RTC over MAC 完整实现方案（落地版）

日期：2026-11-09
场景：树莓派 5（STA，MT7921AU）无线 5G 上行 → BPI-R4 AP（OpenWrt，桥接）→ 有线参考接收端
范围：**只做媒体面**；复用标准开源 RTP/RTCP/SRTP，只替换传输出口，不重写 RTC。

> 本方案整合 `RTC_OVER_MAC_MEDIA_PLAN_20261109.md`，并修正其中四处已知缺陷（见 §9.1–9.4）。旧方案文档保留为历史版本。

---

## 0. 一句话目标与边界

### 0.1 要做什么

```text
标准 RTP/RTCP/SRTP 媒体面
   ├─ Baseline：走 UDP/IP（对照组）
   └─ Target  ：去掉 UDP/IP，直接走以太网 L2 帧（EtherType 0x88B5），经 802.11 空口到 AP
```

- 1080p24/25/30，H.264；Opus 48 kHz 立体声；
- 目标码率 10 / 15 / 20 Mbps；
- A/V 同步 p95 ≤ 40 ms（干净链路）；
- 两臂同一套 RTP/RTCP/SRTP 代码、同一素材、同一编码、同一接收端，顺序跑，做差分对比。

### 0.2 明确不做

- ICE/STUN/TURN、NAT 穿透、DTLS 握手（第一阶段 PSK SRTP）；
- 完整 WebRTC API、浏览器互通；
- DataChannel/SCTP、simulcast/SVC、多方/SFU、BUNDLE；
- AEC/AGC/PLC 音频前后处理、REMB；
- AP 上实时解码 1080p；
- **本方案不做 on MAC**：不夺取 802.11 头生成、重传、聚合的控制权（那是下一阶段目标，见 §10.5）。

### 0.3 over MAC 与 on MAC 的判据（唯一一条）

`send()` 的第二个参数是「一个 MAC 地址」→ **over MAC**（驱动拼 802.11 头）；
是「已经带好 802.11 头的一整帧」→ **on MAC**（自己拼头、自己控重传/聚合）。

当前场景属于 **over MAC**：以太网帧里目的 MAC = 接收端 MAC，源 MAC = Pi `wlan1` MAC，EtherType `0x88B5`，802.11 头仍由驱动生成。

---

## 1. 现状盘点（2026-11-09 实测）

### 1.1 树莓派 5（RPI-5）

| 项 | 实测值 |
|---|---|
| OS | Debian GNU/Linux 13 (trixie)，aarch64，带桌面 |
| 登录用户 | `bai`（SSH key：`id_ed25519_pi_rtc`） |
| `eth0`（管理） | `192.168.240.153/24`，UP |
| `wlan1`（媒体，MT7921AU） | `192.168.240.126/24`，UP，5G `BPI-R4-5G` |
| `wlan0`（板载 brcmfmac） | DOWN |
| 家目录 | 干净，无 rtc 项目代码、无素材以外文件 |

### 1.2 已装软件（含溯源）

| 软件 | 版本 | 安装时间 | 性质 |
|---|---|---|---|
| ffmpeg / ffprobe | 7.1.5（`+rpt2`） | 2026-10-06 08:24 | 镜像自带 |
| VLC | 3.0.24 | 2026-11-08 18:28 | 后续安装（通用播放器，非项目实现） |
| GStreamer | 1.26.2（Debian 包，非源码编译） | 2026-11-09 20:02 | 本项目媒体层 |
| 已验证元件 | `rtpbin` `rtpjitterbuffer` `srtpenc/srtpdec` `rtpulpfecenc/dec` `rtph264pay/depay` `rtpopuspay/depay` `opusenc/dec` `aacparse` `rtpmp4gpay/depay` `avdec_aac` `rtpssrcdemux` `audioconvert` `audiorate` | — | — |

### 1.3 AP（BPI-R4，OpenWrt）

| 项 | 值 |
|---|---|
| 管理 | `root@192.168.240.1`，key 免密可用 |
| 桥 | `br-lan`，含 `lan1` `phy0.0-ap0` `phy0.1-ap0` |
| 5G | `phy0.1-ap0`，MAC `36:19:86:e0:2e:0f`，SSID `BPI-R4-5G`，ch149(5745 MHz)，HE80 |
| 2.4G | SSID `BPI-R4`，ch6，HE20 |
| 板端限制 | busybox；无 `nohup/setsid/pkill`；`ip` 无 `-br`；`station dump` 饱和时阻塞 4–5 s；一次只发一条命令 |

### 1.4 素材与产物（Windows 本机）

目录：`_work_final/rtc/media/testset_1080p/`

| 文件 | fps | 时长 | 视频码率 | 音频 | 用途 |
|---|---:|---:|---:|---|---|
| `1080p24_1_sintel_trailer_52s.mp4` | 24 | 52.21 s | 2108 kb/s | AAC 立体声 | 24fps 备用 |
| `1080p24_2_caminandes_90s.mp4` | 24 | 90.04 s | 6999 kb/s | AAC 立体声 | 24fps 内容 |
| `1080p25_3_bbb_trailer_33s.mp4` | 25 | 32.99 s | 7162 kb/s | AAC 5.1 | 25fps 矩阵（需下混） |
| `1080p30_1_artemis_origins_85s.mp4` | 30 | 85.33 s | 4999 kb/s | AAC 立体声 | **smoke 主素材**（已在 Pi `/home/bai/rtc_test/`） |
| `1080p30_2_artemis_avatar_76s.mp4` | 30 | 75.77 s | 4997 kb/s | AAC 立体声 | 30fps 内容 |
| `1080p30_3_artemis_recap_90s.mp4` | 30 | 90.07 s | 5021 kb/s | AAC 立体声 | 30fps 内容 |
| `anchor_1080p30_clapper_10s.mkv` | 30 | 10.00 s | 21 kb/s 合成信号 | Opus 48k 立体声 | **音画锚点**（每秒白闪帧 + 50 ms 1 kHz 短音，10 对，自检对齐 OK；SHA256 `ff09289c…de25`） |

### 1.5 已完成 / 未完成

- ✅ 旧 RTC2 假设已撤回：Pi 上不存在"旧媒体层"；RTC2 是 Windows 私有协议（`MAGIC 0x52544332`），归档只读，不再使用。
- ✅ 本地 RTP 打包探针：视频 5933 包 seq gap=0，1 SSRC，PT=96；音频 344 包 PT=111；PASS=5 / FAIL=0（打包层验证，未做回环解码与 rtpbin SR 验证）。
- ✅ 锚点素材生成脚本：`_work_final/rtc/media/make_anchor_material.py`。
- ⬜ UDP baseline、SRTP、真实无线链路、L2 元素、反馈机制、矩阵测试、AP 接收端：均未开工。

---

## 2. 总体架构

### 2.1 测试拓扑（三条线各干各的活）

```text
                     BPI-R4 AP（OpenWrt, br-lan, 192.168.240.1）
                    /        |         \
             LAN1 有线    LAN2 有线    Wi-Fi 5G phy0.1-ap0
               |            |              |
        管理 SSH/抓包   参考接收端        Pi 5 wlan1（媒体上行）
        （笔记本）    （有线，媒体终点）   90:de:80:1c:6a:7a / .126
                                           |
                                       Pi 5 eth0（管理）.153
```

| 线 | 角色 | 承载 | 能不能改走无线 |
|---|---|---|---|
| 笔记本 ↔ AP LAN | 管理 | SSH、抓包、看日志 | 技术上可以，不该走（见 §9.5） |
| Pi `eth0` ↔ AP LAN | 管理 | SSH、传文件、看温度 | 不该走（同上） |
| Pi `wlan1` ↔ AP 5G | **被测媒体** | RTP/RTCP/SRTP 帧 | —— |
| 参考接收端 ↔ AP LAN | 媒体终点 | 收 RTP、解码、落盘 | **不能挂 WiFi**（两跳空口 + 自干扰，见 §9.5） |

### 2.2 两条媒体路径（单变量对比）

```text
Baseline（UDP/IP）：
  Pi wlan1 → RTP/RTCP → SRTP → UDP/IP → AP 桥 → 有线 → 参考接收端

Target（L2）：
  Pi wlan1 → RTP/RTCP → SRTP → L2 shim(12B) → 以太网帧/802.11 → AP 桥 → 有线 → 参考接收端
```

两臂必须：同一素材、同一编码、同一 GOP、同一 AP 信道、同一接收端；**顺序跑**，不能同时跑（同信道互相抢空口）。

### 2.3 协议栈

```text
H.264 / Opus
   │  RFC 6184（FU-A/STAP-A） / RFC 7587
RTP / RTCP                     RFC 3550；SR/RR/NACK/PLI
   │
SRTP                          RFC 3711；实验室 PSK
   │
┌─────────────┬──────────────┐
│ UdpTransport │ L2Transport  │  ← 唯一被替换的传输缝
│ UDP socket  │ AF_PACKET 帧 │
└─────────────┴──────────────┘
Ethernet II / 802.11 MAC（驱动生成 802.11 头）
```

### 2.4 参考接收端两种形态

| 形态 | 说明 | 用途 |
|---|---|---|
| R1 参考接收 | AP 只做 L2 桥，有线 Linux/Windows 跑 GStreamer | 第一阶段 baseline / 功能 / A-V sync |
| R2 AP 接收 | AP 上跑 Go/Pion 静态二进制，只 depacketize / SRTP / RTCP / 落盘 | 第二阶段"AP 是 RTC 端点" |

> AP 无 Python/Go/FFmpeg/GStreamer，第一阶段不在 AP 上装完整媒体栈。

---

## 3. 复用、适配、裁剪清单

### 3.1 直接复用（标准开源，一行不改）

| 功能 | 标准/实现 | 说明 |
|---|---|---|
| RTP 打包/序号/时间戳/SSRC | RFC 3550，GStreamer `rtph264pay`/`rtpopuspay` | 头 12 B，无 IP/端口/校验和 |
| RTCP SR/RR、NACK、PLI | RFC 3550 / 4585 / 5104，`rtpbin` | SR 的 NTP/RTP 映射是同步锚点 |
| SRTP 加解密/重放保护 | RFC 3711，`srtpenc/srtpdec`（libsrtp2） | HMAC-SHA1-80，强于 UDP 反码校验和 |
| 抖动缓冲/乱序 | `rtpjitterbuffer` | 含 retransmission 支持 |
| H.264 分片 | RFC 6184 FU-A / STAP-A | 大帧靠 FU-A，不做 IP 式分片 |
| Opus 负载 | RFC 7587 | 一包一帧 |
| A/V 同步 | RTCP SR 双时间戳 + 音频主时钟 | 不依赖 NTP 服务器、不经过 IP |

### 3.2 七个适配点（去 UDP/IP 后受影响，逐项打补丁）

| # | 适配点 | UDP/IP 下 | L2 下方案 |
|---|---|---|---|
| 1 | 编址 | IP + 端口五元组 | MAC 地址 + `flow_id`（u16） |
| 2 | 分流 | 端口区分 RTP/RTCP/音视频 | shim `type` 字段 + SSRC，`rtpssrcdemux` 二次分流 |
| 3 | MTU / 大帧 | IP 分片 | MTU 1200；视频靠 FU-A；RTCP/控制超 MTU 走 shim 分片 |
| 4 | 完整性 | UDP 16 位反码校验和 | SRTP auth tag + shim 头单独 HMAC |
| 5 | QoS | DSCP/ECN | `SO_PRIORITY` → `skb->priority` → WMM AC；AP 侧读 `aql_pending`/airtime |
| 6 | 发现 | ICE/STUN candidate | 静态配置 JSON（src/dst MAC、flow_id、SSRC、PT）；第二阶段再补 L2 发现 |
| 7 | 遥测 | ICMP ping、RTT | RTCP RR RTT + AP `station dump`（airtime/retries/rx bytes） |

### 3.3 删除清单（确认不需要，进裁剪候选）

ICE/STUN/TURN、DTLS 握手（第一阶段 PSK）、BUNDLE、SVC/simulcast、DataChannel/SCTP、多方/SFU、浏览器 API、AEC/AGC、RED 音频冗余、组播/广播、TCP fallback、REMB。

### 3.4 禁止裁剪（裁了就坏）

- **RTCP SR**：音画同步唯一锚点；删掉同步永久丢失。
- **SRTP auth tag**：替代 UDP 校验和的完整性来源。
- **RTP 序号/时间戳**：抖动缓冲、乱序、重传、回绕兜底全靠它。

---

## 4. 传输缝（关键设计）

### 4.1 统一接口

```text
DatagramTransport:
  send(pkt, addr)
  recv(timeout) -> (pkt, addr)
  local_addr()
  mtu() = 1200
  set_deadline(t)
  close()
```

两种实现：

```text
UdpTransport  → 标准 UDP socket（baseline）
L2Transport   → AF_PACKET(SOCK_RAW) 绑 wlan1 + EtherType 0x88B5 + shim（target）
```

上层媒体代码只认 `DatagramTransport`，不认 IP/UDP，也不认 MAC。

### 4.2 L2 shim（固定 12 字节，不重复 RTP 的 seq/ts）

```text
偏移  长度  字段
0     1     ver(4) | type(4)      type: RTP / RTCP / control / discovery
1     1     flags                  start/end fragment、keyframe、retransmit
2     2     flow_id (u16)          会话/端点对，映射 SSRC/MID
4     2     payload_len (u16)      本帧负载长度
6     1     ttl                    环路保护
7     1     hdr_len                头长度，便于扩展
8     2     header_crc/hmac (u16)  头完整性；SRTP 不保护 shim 头
10    2     stream_id / reserved   可选流标识；RTP 内部仍用 SSRC
```

- 一个会话一个 `flow_id`；RTP/RTCP 同 flow 内按 `type` 分流；
- 音视频不同 SSRC；
- EtherType 实验用 `0x88B5`，产品化需注册/换标准；
- shim 头单独 HMAC（SRTP 只管 RTP/RTCP 载荷，不管 shim）。

### 4.3 GStreamer 双栈

| 端 | Baseline | Target |
|---|---|---|
| 发送 | `udpsink` | `l2sink`（GstBaseSink：AF_PACKET + shim） |
| 接收 | `udpsrc` | `l2src`（GstBaseSrc：AF_PACKET + 去 shim + 分流） |

其余 pipeline 完全一致；`--transport udp|l2` 切换，不复制媒体代码。
`l2sink/l2src` 写法照抄 GStreamer 自带 `gst-plugins-good/gst/udp/gstudpsink.c`、`gstmultiudpsink.c`，**零改动原有代码**，新增两个文件。

### 4.4 不用本地 UDP 代理

```text
禁止：GStreamer → 127.0.0.1 UDP → l2proxy → L2
```

媒体路径里保留 UDP 就无法证明"去掉 UDP/IP"。代理只能临时调试，不能作为验收路径。

### 4.5 L2 发送/接收要点

- Pi：`AF_PACKET` 绑定 `wlan1`，`SOCK_RAW`，需要 root / `CAP_NET_RAW`；
- 目的 MAC：**参考接收端的单播 MAC**（不是 AP 的 MAC，见 §9.2）；
- 源 MAC：Pi `wlan1` 的 `90:de:80:1c:6a:7a`；
- 不经过 IP 栈；`AF_PACKET` 不查路由表，`bind(("wlan1",0))` 写死网卡；
- AP 侧抓包绑 `phy0.1-ap0`（不是 `br-lan`）。

### 4.6 配置 JSON（第一阶段静态配置，不做 SDP/ICE）

```json
{
  "role": "sender",
  "transport": "l2",
  "iface": "wlan1",
  "src_mac": "90:de:80:1c:6a:7a",
  "dst_mac": "<参考接收端有线网卡 MAC>",
  "ethertype": 34997,
  "flow_id": 1,
  "mtu": 1200,
  "video": {"codec": "h264", "pt": 96, "ssrc": 1001},
  "audio": {"codec": "opus", "pt": 111, "ssrc": 1002},
  "srtp": {"key_file": "/etc/rtc/srtp.key"}
}
```

---

## 5. 媒体管线

### 5.1 发送端

```text
matroskademux
  ├── h264parse → rtph264pay → queue → srtpenc → l2sink/udpsink
  └── opusparse → rtpopuspay  → queue → srtpenc → l2sink/udpsink

rtpbin：发 RTP/RTCP；收 RTCP RR/NACK/PLI；提供 SR/RR、retransmission
```

要点：
- `rtpbin` 负责 RTCP SR/RR 与反馈；
- `srtpenc` 在 RTP/RTCP 之后、传输之前；
- `l2sink` 负责 shim、`flow_id`、MTU、目的 MAC；
- **pacing 不由 `queue` 承担**（`queue` 只缓冲不调速）；M1 文件源 CBR 不需要 pacing，实时采集/20 Mbps 阶段需要独立 pacer（`identity` + 定时 sleep 或 `rtpbin` 限速），见 §9.3。

### 5.2 接收端

```text
l2src/udpsrc → srtpdec → rtpbin
                    ├── rtpjitterbuffer → rtph264depay → h264parse → avdec_h264 → sink/file
                    └── rtpjitterbuffer → rtpopusdepay → opusdec → audioconvert → audio sink/file
```

要点：
- `l2src` 去 shim，按 `type` 分 RTP/RTCP；
- `srtpdec` 解密/校验；
- `rtpjitterbuffer` 处理乱序/抖动/重传；
- `rtpbin` 用 RTCP SR 做时间轴映射；
- 播放以音频 sink 为主时钟，视频跟随；
- 录制时用 `identity`/pad probe 记录 PTS 与到达时间，离线算 A/V skew。

### 5.3 音视频同步

```text
RTP timestamp(90 kHz) + RTCP SR(NTP/RTP)
        ↓
接收端共同墙钟
        ↓
play = PTS + tmin + D
```

- 音频主时钟，视频丢帧/重复追赶；`D` 初始 100–200 ms，按抖动调整；
- 目标 p95 ≤ 40 ms；
- 不需要 NTP 服务器：SR 的 NTP 时间戳来自发送端本地系统时钟，不经过 IP；
- 24/25/30 fps 的 RTP 步长 3750/3600/3000（90 kHz 整除），整数无取整误差。

### 5.4 恢复机制（M5 补齐）

| 机制 | 实现 |
|---|---|
| NACK | `rtpbin` `do-retransmission` / `rtpjitterbuffer` |
| PLI | 解码错误/整帧丢失时请求 IDR |
| RTX | 独立 SSRC 重传 |
| FEC | `rtpulpfec`（RFC 5109）/ FlexFEC（RFC 8627），后续 |
| 过期帧丢弃 | 按 PTS 截止时间，不救已过期帧 |

---

## 6. 分阶段实施（M0–M8）

每阶段门禁：上一阶段验收全过，才进下一阶段；每阶段留 pcap + 指标 + 日志。

### M0 准备（2–3 天）

| 任务 | 验收 | 现状 |
|---|---|---|
| 冻结 RTC2 到 `legacy/`，只读归档 | 仓库内不再引用 RTC2 代码 | ⬜ |
| 建目录结构（§8） | 目录/配置骨架就位 | ⬜ |
| 素材预处理：`1080p30_1` 派生 10/15/20 Mbps + Opus 48k；固定 GOP；`-bf 0`；MKV | ffprobe 实测码率/GOP/声道正确；SHA256 入 MANIFEST | ⬜（锚点素材已就绪） |
| 确认参考接收端形态（R1） | 接收端机器/系统/GStreamer 版本定下来 | ⬜ **开放问题 §10.1** |

### M1 UDP baseline，视频-only（3–5 天）

| 任务 | 验收 |
|---|---|
| 本地回环（127.0.0.1）：文件 → RTP → UDP → depay → 解码 → 落帧 | 源帧数 = 解码帧数，无解码错误 |
| RTP 头字段核查 | V=2、PT=96、seq 连续无 gap、SSRC 单一稳定、时间戳步长 3000/帧 |
| 真实无线链路：Pi `wlan1` → AP → 有线接收端，视频-only | AP `tcpdump -i phy0.1-ap0` 抓到 RTP；帧完整率/解码成功率达标 |
| 链路指标记录 | 时延、抖动 p50/p95、帧完整率、解码率、Pi CPU/温度、AP airtime/retries |
| 路由出口核查 | `ip route get <接收端IP> from 192.168.240.126` 必须显示 `dev wlan1`（§9.1） |

### M2 UDP + Opus + A/V sync（3–5 天）

| 任务 | 验收 |
|---|---|
| 音频双流：Opus RTP，PT=111，独立 SSRC | 打包/回环解码无错，seq 连续 |
| `rtpbin` 双流 + RTCP SR | 两个 SSRC；SR 含 NTP↔RTP 映射；两路 PTS 进同一时钟 |
| 锚点素材量基准偏差 | 白帧 PTS 与短音起点 PTS 差 p50/p95 记录入台账（这是 L2 要减的基准） |
| SRTP 加解密 | `srtpenc/srtpdec` 跑通；配 key Wireshark 可解，不配看不到载荷 |

### M3 L2 视频-only（5–8 天）

| 任务 | 验收 |
|---|---|
| `l2sink`/`l2src` 最小版本（AF_PACKET + shim 打包/解包 + type 分流） | 本地回环通；独立目录/端口，不碰 UDP 会话 |
| 同一 pipeline 切 L2，视频-only 过无线 | AP 侧抓到 `0x88B5` 帧；解码帧数与 baseline 一致 |
| 无 IP/UDP 核查 | L2 pcap 中无 IP 头、无 UDP 头；只有 shim + RTP/RTCP/SRTP |
| 与 UDP baseline 差分 | 帧完整率/解码率/抖动/时延对比，差异归因到具体层/字段 |

### M4 L2 + Opus + A/V sync（3–5 天）

| 任务 | 验收 |
|---|---|
| 音频走 L2，RTP/RTCP 同 flow 按 type 分流 | 音视频 SSRC 不串流；RTCP SR 通道正常 |
| 锚点素材量 L2 偏差 | `L2 skew − UDP 基准 skew` = 换传输造成的同步偏差；p95 ≤ 40 ms |

### M5 NACK/PLI/RTX/FEC（5–7 天）

| 任务 | 验收 |
|---|---|
| 注入 0.01/0.1/0.5% 丢包 + 突发 | NACK/RTX 恢复；PLI 请求 IDR；整帧废弃率达标 |
| FEC（ULPFEC 起步） | 残存帧废弃率下降；记录 FEC 开销 |
| 过期帧丢弃策略 | 过期帧不重传，pacing/缓冲不堆积 |

### M6 帧率 × 码率矩阵（5–7 天）

| 用例 | 配置 |
|---|---|
| FPS | 24/25/30 各一条，15 Mbps + Opus |
| Bitrate | `1080p30_1`，10/15/20 Mbps |
| Content | 六条全部，15 Mbps + Opus |
| Long | `1080p30_1`，15 Mbps，10 min（seq 回绕/稳定性） |

### M7 AP Go/Pion 接收端（7–10 天）

| 任务 | 验收 |
|---|---|
| Go/Pion 静态二进制：SRTP depacketize、RTCP、落盘 | AP 上无媒体栈依赖；二进制可执行 |
| L2 收包（`mdlayher/packet`） | AP 侧收 `0x88B5` 帧并解 shim |
| 与 R1 参考接收结果对齐 | 帧完整率/指标一致 |

### M8 QoS / 遥测 / 长时（7–10 天）

| 任务 | 验收 |
|---|---|
| WMM AC 队列下发 | `SO_PRIORITY` → `skb->priority` → AC 映射被驱动采纳（实测） |
| AP 遥测 | 读 `aql_pending`、per-STA airtime、retries；写入指标表 |
| 长时/多 STA 稳定性 | 10 min+ 长跑；无泄漏、无 SSRC 漂移 |
| （可选）码率自适应 | 先 GCC 草案评估；第一阶段不做 |

---

## 7. 测试方案

### 7.1 三层递进（每层只加一类变量）

**L0 本地回环（127.0.0.1，不碰网络）**——把软件问题和网络问题分开：

| # | 测试 | 通过标准 |
|---|---|---|
| 0.1 | 视频打包 + 回环解码 | 源帧数 = 解码帧数，无解码错误 |
| 0.2 | RTP 头字段 | V=2、PT=96、seq 连续、SSRC 稳定、时间戳步长正确 |
| 0.3 | 音频打包 + 回环解码 | PT=111、seq 连续、Opus 解码无错 |
| 0.4 | 双流 + rtpbin | 两个 SSRC；SR 含 NTP↔RTP 映射 |
| 0.5 | 锚点回环 | 白帧/短音 PTS 差接近 0（几 ms 内） |

**L1 真实链路 UDP**——量 baseline 指标（§6 M1/M2）。

**L2 标准一致性**——不需要对照组，对照物是 RFC + 独立对端：

| # | 测试 | 方法 |
|---|---|---|
| 2.1 | 线格式解析 | Wireshark 正确解析 RTP/RTCP/SRTP，无 unknown |
| 2.2 | 字段规则 | seq/时间戳单调、SSRC 不变、PT 一致；SR 映射自洽 |
| 2.3 | 独立对端交叉验证 | Pion/aiortc 收 GStreamer 发的流能解码（或反向） |
| 2.4 | 长时稳定性 | 10 min 长跑，回绕/泄漏/SSRC 漂移检查 |

### 7.2 测试矩阵

| 用例 | 素材 | 配置 |
|---|---|---|
| Smoke | `1080p30_1` | 10 Mbps，视频-only |
| Audio | `1080p30_1` | 15 Mbps + Opus |
| FPS | 24/25/30 各一条 | 15 Mbps + Opus |
| Bitrate | `1080p30_1` | 10/15/20 Mbps |
| Content | 六条全部 | 15 Mbps + Opus |
| Loss | `1080p30_1` | 0.01/0.1/0.5% + 突发 |
| Long | `1080p30_1` | 15 Mbps，10 min |

### 7.3 八项必测指标

| 指标 | 定义 | 采集点 |
|---|---|---|
| 帧完整率 | 完整收到的帧 / 总帧数（最核心） | 接收端 depay 统计 |
| 解码成功率 | 成功解码帧 / 完整帧 | 解码器错误计数 |
| 端到端时延 | 到达 → 播放延迟（L2 阶段无 NTP 客户端，单向墙钟时延测不了，见 §9.4） | 接收端内部时间戳 |
| 抖动 | 到达间隔 p50/p95；JB 深度 | `rtpjitterbuffer` 统计 |
| A/V 同步偏差 | 锚点白帧 PTS − 短音起点 PTS，p50/p95 | 接收端双路 probe |
| 画质 | PSNR/SSIM/VMAF，对比源片 | 离线分析脚本 |
| Pi 资源 | CPU、内存、温度、USB 占用 | Pi 侧 `top`/`vcgencmd` |
| AP 空口 | airtime、busy、MCS/RSSI、retry/duplicate、rx bytes | AP `station dump`/`iw` |

### 7.4 公平对比规则

- 同一 AP、同一信道、同一接收端；同一编码器/GOP/码率；
- UDP 与 L2 **顺序跑**；每条件至少 3 轮取中位数；奇偶翻转运行顺序抵消射频慢漂移；
- 丢包用确定性规则注入（如每 200 分片丢第 1 个），两臂注入量相同；
- 每轮日志单独存，指标即时追加 CSV；pcap 全部保留。

### 7.5 已知测量限制

- **L2 阶段测不了单向墙钟时延**：无 IP、无 NTP 客户端；只能测 RTCP RR 的 RTT + 接收端"到达→播放"内部延迟。需要单向时延结论时，用锚点素材双端录屏/录波交叉对齐。
- 锚点测量分辨率：视频 ±33.3 ms（30fps 一帧），音频 ±20 ms（分析窗）；需要更细另出 60 fps 版本。

---

## 8. 目录结构与代码分工

```text
rtc-over-mac/
  configs/
    sender_udp.json  sender_l2.json
    receiver_udp.json receiver_l2.json
  media/
    prepare_testset.py          # 派生 10/15/20M + Opus
    manifest.csv
  gst/
    l2sink/                     # GstBaseSink: AF_PACKET + shim
    l2src/                      # GstBaseSrc: AF_PACKET + shim + 分流
    common/                     # shim pack/unpack、HMAC、flow_id
  app/
    send.sh                     # GStreamer 发送（--transport udp|l2）
    recv.sh                     # GStreamer 接收
    analyze.py                  # PSNR/SSIM/VMAF/A-V skew
  ap/
    receiver/                   # M7 Go/Pion 静态接收器
  test/
    run_matrix.py
    impairment.py
  docs/
  legacy/                       # RTC2 只读归档
```

- `l2sink/l2src` 参照 GStreamer 自带 `gstudpsink.c` / `gstmultiudpsink.c`；
- 第一阶段可用 `appsink/appsrc` + 独立 L2 进程做功能验证，但**验收路径必须是正式元素，无本地 UDP**；
- 密钥放配置文件/环境变量，权限 600，不进 git。

---

## 9. 风险、对策与已识别缺陷修正

### 9.1 缺陷①：同网段双直连路由（必须先修）

`eth0=.153` 与 `wlan1=.126` 同在 `192.168.240.0/24`，两条重合直连路由、同 metric，内核可能选 `eth0` 出口；`sendto()` 照样返回成功、不报错，媒体偷走有线。

三条固定手段（任选其一，推荐独立子网）：

1. **独立子网**：`wlan1` 改 `192.168.241.x`，与管理面物理隔离（最干净，顺手做媒体隔离）；
2. **策略路由**：`ip rule add from 192.168.240.126 lookup 100` + `ip route add 192.168.240.0/24 dev wlan1 table 100`；
3. **`SO_BINDTODEVICE`**：socket 绑 `wlan1`（注意：GStreamer `udpsink` 的 `bind-address` 只改源 IP，不改出口网卡，给不了这个）。

**判据（M1 前置检查）**：`ip route get <接收端IP> from 192.168.240.126` 必须显示 `dev wlan1`。
**四条硬证据**：`eth0` TX 增量≈0；`wlan1` TX 增量≈码率×时长；AP `tcpdump -i phy0.1-ap0` 抓到 `0x88B5`；`station dump` 的 rx bytes 增长（最硬，无法伪造）。

### 9.2 缺陷②：目的 MAC 不能填 AP MAC

目的 MAC 必须是**参考接收端有线网卡的单播 MAC**。填 AP 的 MAC 会被 AP 本地收下、不转发；目的 MAC 未知/广播时，桥会泛洪所有 LAN 口（包括 Pi 自己接的 `eth0`），Pi 会收到自己发的帧。

### 9.3 缺陷③：pacing 不由 queue 控制

`queue` 只做缓冲，不做调速。20 Mbps 突发（一帧 ~71 包）需要独立 pacer：`identity` + 定时 sleep，或 `rtpbin` 限速；M1 文件源 CBR 阶段可暂缓，实时采集/高码率阶段必须补。

### 9.4 缺陷④：单向时延在 L2 阶段不可测

见 §7.5。不要在 L2 指标表里写"单向时延"，改用 RTT + 到达→播放内部延迟。

### 9.5 风险：管理面与媒体面混用

- SSH 走无线会和媒体抢空口、污染归因；链路一饱和 SSH 卡死/失联，恰在最需要观测时失明。
- 接收端挂 WiFi = 两跳空口 + 两个 STA 抢同信道自干扰，数据全废。**接收端必须挂 AP 有线口。**

### 9.6 其他风险

| 风险 | 对策 |
|---|---|
| AP 无 GStreamer/Python | R1 有线参考接收先行；R2 用 Go 静态二进制 |
| GStreamer L2 元素开发量 | 先 `appsink/appsrc` 验证功能，再转正式元素 |
| Pi 高码率软编 | 第一阶段喂预编码文件；实时编码用 `h264_v4l2m2m`/x264 实测 CPU |
| 空口抖动/省电 | 5G、80 MHz、单媒体接口、关省电；AP 侧监控 |
| 自定义 EtherType 被桥丢 | 先 `tcpdump` 验证；必要时 media VLAN |
| 多网卡干扰 | 只启用 `wlan1`；`wlan0` 保持 DOWN |
| 头开销收益有限 | 每包省 24 B，20 Mbps 约 2.0%；**真正收益是 MAC 感知控制**（AC 队列、队列深度、airtime、过期帧不重传），不靠省头字节 |

---

## 10. 开放问题（需拍板）

| # | 问题 | 选项 | 影响 |
|---|---|---|---|
| 10.1 | 参考接收端用什么机器 | 另一台 Linux 有线机 / Windows 装 GStreamer / Pi 自环（仅 L0） | 决定 M1 真实链路能否开工 |
| 10.2 | 媒体面寻址隔离方式 | 独立子网 192.168.241.x / 策略路由 / `SO_BINDTODEVICE` | 见 §9.1 |
| 10.3 | 首测码率档位 | 先 10 Mbps 跑通，再补 15/20 | 建议如此 |
| 10.4 | 是否并行做音频 | 建议 M1 视频-only，M2 再加 Opus | 单变量原则 |
| 10.5 | on MAC 范围 | 本方案只到 over MAC；on MAC（自拼 802.11 头/重传/聚合）需改 mac80211 或 monitor 注入，属下一阶段 | 本方案不承诺 |
| 10.6 | AP 端是否需实时解码 | 第一阶段落盘 + 离线分析；不做实时解码 | —— |
| 10.7 | `SO_PRIORITY`→AC 映射能否被驱动采纳 | 只能实测，M8 验证 | 不预设结论 |

---

## 11. 当前下一步（M0 收尾 + M1 启动）

1. 把 `anchor_1080p30_clapper_10s.mkv` 传到 Pi（178 KB，走 `eth0`）；
2. 确认参考接收端形态（§10.1）；
3. 预处理 `1080p30_1` 10 Mbps + Opus（视频 `-c:v copy` 起步，不重编码）；
4. Pi 上跑 L0 本地回环：视频-only → RTP/UDP 127.0.0.1 → 解码落帧；
5. 核查 `ip route get` 出口为 `wlan1`；
6. 跑通后再上真实无线链路，记录 BL-01～BL-12 基线指标。

> 基线未冻结前，不动 L2；L2 未验收前，不做码率矩阵和反馈机制。
