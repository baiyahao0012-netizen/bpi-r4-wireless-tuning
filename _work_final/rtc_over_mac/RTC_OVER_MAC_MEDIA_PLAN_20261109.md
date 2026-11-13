# RTC over MAC 媒体面完整方案

日期：2026-11-09  
目标链路：Raspberry Pi 5（STA，MT7921AU）→ BPI-R4（AP）→ 有线参考接收端  
素材：`_work_final/rtc/media/testset_1080p/` 六条 1080p24/25/30 带音频视频  
范围：**只做媒体面**，不做完整 WebRTC。

---

## 0. 目标与边界

### 0.1 目标

```text
Pi 5（STA） --802.11 上行--> BPI-R4 AP --Ethernet--> 参考接收端
```

- 1080p24/25/30，H.264；Opus 48 kHz；
- 目标码率 10 / 15 / 20 Mbps；
- 音视频同步 p95 ≤ 40 ms；
- 媒体面去掉 UDP/IP，使用标准 RTP/RTCP/SRTP；
- 先做 UDP/IP baseline，再换 L2，做差分对比；
- 最终把接收端从“有线参考机”移植到 AP。

### 0.2 不做

- ICE/STUN/TURN、NAT 穿透；
- 完整 WebRTC API、浏览器互通；
- DataChannel/SCTP；
- simulcast/SVC、多方/SFU；
- AP 上实时解码 1080p；
- 第一阶段的 DTLS/802.1X 产品级安全（先 PSK SRTP）。

### 0.3 验收总目标

| 项 | 目标 |
|---|---|
| 标准性 | Wireshark 能按 RTP/RTCP 解析 |
| 无 IP/UDP | L2 pcap 中只有 EtherType + RTP/RTCP/SRTP |
| 视频 | 1080p24/25/30，10/15/20 Mbps 可解 |
| 音频 | Opus 48 kHz，无爆音/半速 |
| A/V sync | p95 ≤ 40 ms（干净链路） |
| 画质 | PSNR/SSIM/VMAF 不低于 UDP baseline |
| 丢包 | 0.1% 包丢失下帧完整率 ≥ 95%（NACK/RTX/FEC） |
| 回归 | UDP 与 L2 使用同一套 RTP/RTCP/SRTP 代码 |

---

## 1. 设计原则

1. **传输替换，不重写 RTC。**  
   RTP/RTCP/SRTP/编解码/抖动缓冲保持标准实现，只替换 `send/recv`。
2. **同一套代码跑两种传输。**  
   `--transport udp|l2`，不是复制两份媒体代码。
3. **先 baseline，再裁剪。**  
   没有 UDP baseline，就没有“标准答案”。
4. **先视频-only，再加音频。**  
   先排除编码/封装变量，再做 A/V sync。
5. **先文件，再实时采集。**  
   六条素材先跑通，再接摄像头/麦克风。
6. **一次只改一个变量。**  
   编码器、GOP、码率、传输、缓冲，不能同时变。
7. **所有结论有 pcap/指标。**  
   不靠“看起来能播”。

---

## 2. 系统架构

### 2.1 测试拓扑

```text
                 BPI-R4 AP（OpenWrt）
                /          |           \
          LAN1(eth)    LAN2(eth)      Wi-Fi 5G
             |             |               |
       Windows 笔记本   参考接收端       Pi 5 wlan1
       管理/SSH         （有线）         媒体上行
```

- Pi `eth0`：管理，`192.168.240.153`；
- Pi `wlan1`：媒体，`192.168.240.126`，无默认路由；
- AP `br-lan`：`192.168.240.1`；
- 参考接收端：有线接 AP，跑 GStreamer 接收；
- AP 只做无线接入 + L2 bridge（第一阶段）。

### 2.2 两条媒体路径

**Baseline：UDP/IP**

```text
Pi wlan1 → RTP/RTCP → SRTP → UDP/IP → AP → 有线 → 参考接收端
```

**Target：L2**

```text
Pi wlan1 → RTP/RTCP → SRTP → L2 shim → 802.11 → AP → 有线 → 参考接收端
```

两臂必须：

- 同一素材、同一编码、同一 GOP；
- 同一 AP、同一信道、同一接收端；
- **顺序跑**，不能同时跑（同信道会互相抢空口）。

### 2.3 AP 端接收的两种形态

| 形态 | 说明 | 用途 |
|---|---|---|
| **R1 参考接收** | AP 只做 L2 bridge，有线 Linux/Windows 跑 GStreamer | 第一阶段 baseline/功能/A-V sync |
| **R2 AP 接收** | AP 上跑 Go/Pion 接收器，只 depacketize/SRTP/RTCP/落盘 | 第二阶段“AP 是 RTC 端点” |

> AP 目前没有 Python/Go/FFmpeg/GStreamer。不要在 AP 上装完整媒体栈；R1 先做参考，R2 用静态 Go 二进制。

---

## 3. 协议栈

### 3.1 总栈

```text
H.264 / Opus
   │
RTP / RTCP
   │
SRTP
   │
L2 shim
   │
Ethernet / 802.11 MAC
```

### 3.2 标准部分

| 层 | 选择 |
|---|---|
| 视频负载 | H.264 RTP，RFC 6184（单 NAL / FU-A / STAP-A） |
| 音频负载 | Opus RTP，RFC 7587 |
| RTP/RTCP | RFC 3550；SR/RR、NACK、PLI |
| 加密 | SRTP，RFC 3711；实验室 PSK |
| 抖动缓冲 | GStreamer `rtpjitterbuffer` |
| 重传 | RTX/NACK；GStreamer `rtpbin` retransmission |
| FEC | ULPFEC/FlexFEC（后续） |
| 同步 | RTCP SR 的 NTP/RTP 映射 |

### 3.3 L2 shim

建议 12 字节，**不要重复 RTP 的 seq/timestamp**：

固定 12 字节：

```text
偏移  长度  字段
0     1     ver(4) | type(4)
1     1     flags
2     2     flow_id (u16)
4     2     payload_len (u16)
6     1     ttl
7     1     hdr_len
8     2     header_crc/hmac (u16)
10    2     stream_id / reserved (u16)
```

| 字段 | 说明 |
|---|---|
| `ver` | shim 版本 |
| `type` | RTP / RTCP / control / discovery |
| `flags` | start/end fragment、keyframe、retransmit |
| `flow_id` | 会话/端点对；映射到 SSRC/MID |
| `payload_len` | 本帧负载长度 |
| `ttl` | 环路保护 |
| `hdr_len` | 头长度，便于扩展 |
| `header_crc/hmac` | 头完整性；SRTP 不管 shim 头 |
| `stream_id` | 可选流标识；RTP 内部仍用 SSRC |

EtherType：实验用 `0x88B5`；产品需注册/改用标准。

### 3.4 复用与 MTU

- 一个会话一个 `flow_id`；
- RTP/RTCP 在同一个 flow 内按 `type` 分流（或 RFC 5761 mux）；
- 音视频用不同 SSRC，必要时用 RTP MID/RID；
- `MTU = 1200`，RTP 包不得超过；
- 视频大帧由 H.264 FU-A 处理，**不要做 IP 式分片**；
- RTCP/控制/DTLS 如果超过 MTU，走 shim 分片。

### 3.5 SRTP 与密钥

- 第一阶段：PSK，`srtpenc`/`srtpdec`；
- 密钥放配置文件/环境变量，权限 600，不进 git；
- shim 头单独 HMAC，防 flow_id/长度篡改；
- 第二阶段：DTLS-SRTP 或 802.1X 引导；
- 局域网也必须加密，不允许明文。

### 3.6 最小 SDP/配置

第一阶段不实现 ICE/SDP 协商，用 JSON：

```json
{
  "role": "sender",
  "transport": "l2",
  "iface": "wlan1",
  "src_mac": "90:de:80:1c:6a:7a",
  "dst_mac": "36:19:86:e0:2e:0f",
  "ethertype": 34997,
  "flow_id": 1,
  "mtu": 1200,
  "video": {"codec": "h264", "pt": 96, "ssrc": 1001},
  "audio": {"codec": "opus", "pt": 111, "ssrc": 1002},
  "srtp": {"key_file": "/etc/rtc/srtp.key"}
}
```

第二阶段再补最小 SDP profile（`m=`/`rtpmap`/`fmtp`/`rtcp-mux`），替换 `c=`/ICE 候选为 L2 地址/flow_id。

---

## 4. 媒体管线

### 4.1 技术选型

| 组件 | 选择 | 原因 |
|---|---|---|
| 发送/参考接收 | **GStreamer 1.26** | Pi 已装 plugins；RTP/RTCP/SRTP/jitter/A-V sync 完整 |
| 媒体预处理 | **FFmpeg** | 已在 Pi/Windows；重编码/Opus 转换 |
| L2 收发 | **自定义 GStreamer `l2sink`/`l2src`** | 不引入本地 UDP 代理 |
| AP 端点（后续） | **Go/Pion 静态接收器** | AP 无 GStreamer/Python；只 depacketize/落盘 |
| 分析 | Python/PyAV + FFmpeg | 解码、PSNR/SSIM/VMAF、统计 |

### 4.2 素材预处理

六条原片是 5–7 Mbps，必须重编码：

```text
H.264 High, yuv420p
CBR 10 / 15 / 20 Mbps
固定 GOP = 1 s（24/25/30 帧）
sc_threshold=0
第一轮 -bf 0
音频：AAC → Opus 48 kHz，立体声；5.1 下混
封装：MKV（H.264 + Opus），保留 PTS
```

建议输出命名：

```text
1080p30_1_artemis_origins_85s_10M_opus.mkv
1080p30_1_artemis_origins_85s_15M_opus.mkv
1080p30_1_artemis_origins_85s_20M_opus.mkv
...
```

每条记录：fps、目标/实际码率、GOP、音频 layout、时长、SHA256。

### 4.3 发送端逻辑管线

```text
matroskademux
  ├── h264parse → rtph264pay → queue → srtpenc → l2sink
  └── opusparse → rtpopuspay → queue → srtpenc → l2sink

rtpbin:
  发送 RTP/RTCP；接收 RTCP RR/NACK/PLI
  提供 SR/RR、retransmission、NACK
```

要点：

- `rtpbin` 负责 RTCP SR/RR 和反馈；
- `srtpenc` 在 RTP/RTCP 之后、L2 之前；
- `l2sink` 负责 shim、flow_id、MTU、目的 MAC；
- 发送端 pacing 由 `queue`/`identity` + 自定义 pacer 或 `rtpbin` 控制；
- 第一轮 CBR，不做 GCC，保证空口不突发。

### 4.4 接收端逻辑管线

```text
l2src → srtpdec → rtpbin
                    ├── rtpjitterbuffer → rtph264depay → h264parse → avdec_h264 → sink/file
                    └── rtpjitterbuffer → rtpopusdepay → opusdec → audioconvert → audio sink/file

rtpbin:
  RTCP SR/RR、NACK/PLI、retransmission
```

要点：

- `l2src` 去掉 shim，按 type 分 RTP/RTCP；
- `srtpdec` 解密/校验；
- `rtpjitterbuffer` 处理乱序/抖动/重传；
- `rtpbin` 用 RTCP SR 做时间轴映射；
- 播放时以音频 sink 为主时钟，视频 sink 跟随；
- 录制时用 `identity`/pad probe 记录 PTS/到达时间，离线算 A/V skew。

### 4.5 音视频同步

```text
RTP timestamp (90 kHz) + RTCP SR (NTP/RTP)
        ↓
接收端共同墙钟
        ↓
play = PTS + tmin + D
```

- 音频为主时钟，视频丢帧/重复追赶；
- `D` 初始 100–200 ms，按抖动调整；
- 目标 p95 ≤ 40 ms；
- 无 IP 不需要 NTP 服务，RTCP SR 自带 NTP 时间戳；
- 24/25/30 fps 的 RTP 步长 3750/3600/3000，整数，便于验证。

### 4.6 恢复机制

第一阶段先做视频-only，恢复后续加：

| 机制 | 实现 |
|---|---|
| NACK | `rtpbin` `do-retransmission` / `rtpjitterbuffer` |
| PLI | 解码错误/整帧丢失时请求 IDR |
| RTX | 独立 SSRC 重传 |
| FEC | `rtpulpfec`/FlexFEC，后续 |
| 过期帧丢弃 | 按 PTS 截止时间，不救已经过期的帧 |

---

## 5. 传输缝（关键设计）

### 5.1 统一接口

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
UdpTransport   → 标准 UDP socket
L2Transport    → AF_PACKET + EtherType + flow_id + shim
```

上层只认 `DatagramTransport`，不认 IP/UDP。

### 5.2 GStreamer 双栈

- 发送端：`udpsink` ↔ `l2sink`；
- 接收端：`udpsrc` ↔ `l2src`；
- 其余 pipeline 完全一致；
- 用环境变量/参数切换，不复制媒体代码。

### 5.3 为什么不用本地 UDP 代理

```text
GStreamer → 127.0.0.1:UDP → l2proxy → L2
```

这会在媒体路径里保留 UDP，无法证明“去掉 UDP/IP”。  
实验室可以临时用于调试，但不能作为验收路径。

### 5.4 L2 实现

- Pi：`AF_PACKET` 绑定 `wlan1`，`SOCK_RAW`；
- AP：`AF_PACKET` 绑定 `phy0.1-ap0` 或 bridge；
- 目的 MAC：参考接收端/AP 的 MAC，单播；
- 源 MAC：Pi `wlan1`；
- EtherType：`0x88B5`；
- 不经过 IP 栈；
- 需要 root/CAP_NET_RAW。

---

## 6. 测试方案

### 6.1 阶段

| 阶段 | 内容 | 通过标准 |
|---|---|---|
| T0 | 素材预处理 | 六条 10/15/20M + Opus 可解，PTS 正确 |
| T1 | UDP/IP baseline，视频-only | 1080p30/10M 无丢帧，RTP 可解析 |
| T2 | UDP baseline + Opus | A/V sync p95 ≤ 40 ms |
| T3 | L2 视频-only | 同 T1，且无 IP/UDP |
| T4 | L2 + Opus | 同 T2，且无 IP/UDP |
| T5 | 24/25/30 + 10/15/20 | 帧率/码率矩阵 |
| T6 | 丢包/突发 | NACK/RTX/FEC 恢复 |
| T7 | 长时/多 STA | 回绕、稳定性、公平性 |

### 6.2 测试矩阵

| 用例 | 素材 | 配置 |
|---|---|---|
| Smoke | `1080p30_1` | 10 Mbps，视频-only |
| Audio | `1080p30_1` | 15 Mbps + Opus |
| FPS | 24/25/30 各一条 | 15 Mbps + Opus |
| Bitrate | `1080p30_1` | 10/15/20 Mbps |
| Content | 六条全部 | 15 Mbps + Opus |
| Loss | `1080p30_1` | 0.01/0.1/0.5% + 突发 |
| Long | `1080p30_1` | 15 Mbps，10 min |

### 6.3 指标

- RTP/RTCP：包数、序号缺口、NACK/PLI/RTX、SR/RR；
- 帧：完整率、解码率、解码错误；
- 抖动：`rtpjitterbuffer` 深度、到达间隔 p95；
- 同步：A/V skew p50/p95/max；
- 时延：单向/端到端；
- 画质：PSNR/SSIM/VMAF；
- 空口：AP 上行 RX airtime、channel busy、MCS/RSSI、retry/duplicate；
- 资源：Pi CPU、内存、USB、温度。

### 6.4 公平对比

- 同一 AP、同一信道、同一接收端；
- 同一编码器/GOP/码率；
- UDP 与 L2 **顺序跑**；
- 每次至少 3 轮，取中位数；
- 保留 pcap 和原始日志。

---

## 7. 目录结构

```text
rtc-over-mac/
  configs/
    sender_l2.json
    sender_udp.json
    receiver_l2.json
    receiver_udp.json
  media/
    prepare_testset.py
    manifest.csv
  gst/
    l2sink/          # GstBaseSink: AF_PACKET + shim
    l2src/           # GstBaseSrc: AF_PACKET + shim
    common/          # shim pack/unpack, HMAC
  app/
    send.sh          # GStreamer 发送
    recv.sh          # GStreamer 接收
    analyze.py       # PSNR/SSIM/VMAF/A-V skew
  ap/
    receiver/        # 后续 Go/Pion AP 接收器
  test/
    run_matrix.py
    impairment.py
  docs/
  legacy/            # 旧 RTC2，只读归档
```

---

## 8. 里程碑

| 里程碑 | 内容 | 估时 |
|---|---|---|
| M0 | 冻结旧 RTC2；建目录；素材预处理 | 2–3 天 |
| M1 | UDP/IP baseline，视频-only | 3–5 天 |
| M2 | Opus + A/V sync（UDP） | 3–5 天 |
| M3 | L2 shim + `l2sink/l2src`，视频-only | 5–8 天 |
| M4 | L2 + Opus + A/V sync | 3–5 天 |
| M5 | NACK/PLI/RTX/FEC | 5–7 天 |
| M6 | 24/25/30 + 10/15/20 矩阵 | 5–7 天 |
| M7 | AP Go/Pion 接收器 | 7–10 天 |
| M8 | QoS/AP 遥测/GCC/长时 | 7–10 天 |

总计约 6–10 周，取决于 GStreamer L2 元素和 AP 接收器的工作量。

---

## 9. 风险与对策

| 风险 | 对策 |
|---|---|
| AP 无 GStreamer/Python | 第一阶段用有线参考接收；最终用 Go/Pion 静态二进制 |
| GStreamer L2 元素开发量 | 先 `appsink/appsrc` + 独立 L2 进程做功能验证，再转正式元素；但验收必须无本地 UDP |
| Pi 1080p30 高码率编码 | 先预编码文件；实时编码用 `h264_v4l2m2m`/x264，实测 CPU |
| Wi-Fi 空口抖动 | 5GHz、80MHz、单 Wi-Fi 接口、关闭省电；AP 侧监控 |
| 20 Mbps 突发 | pacing；固定 GOP；I 帧尖峰单独观察 |
| A/V sync | RTCP SR + 音频主时钟；先文件后实时 |
| 安全 | 先 PSK SRTP；后续 DTLS/802.1X |
| 自定义 EtherType 被桥丢 | 先 `tcpdump` 验证；必要时 media VLAN |
| 多网卡干扰 | 只启用 `wlan1`；板载 `wlan0` 已禁用 |

---

## 10. 明确不做的事

1. 不实现 RTC2。
2. 不实现完整 WebRTC/ICE/STUN/TURN。
3. 不在 AP 上实时解码 1080p。
4. 不把 UDP 和 L2 同时跑。
5. 不用不同编码器/GOP 做对比。
6. 不用“本地 UDP 代理”作为最终 L2 验收路径。
7. 不在第一轮加 GCC/多 STA/加密复杂性。

---

## 11. 下一步

1. 预处理 `1080p30_1_artemis_origins_85s` 到 10 Mbps + Opus 48 kHz；
2. 用 GStreamer 跑 UDP/IP 视频-only，确认 RTP/RTCP/解码；
3. 加 Opus，测 A/V sync；
4. 写 `l2sink/l2src`，把同一个 pipeline 切到 L2；
5. 用 Wireshark 确认无 IP/UDP；
6. 再扩到 15/20 Mbps 和六条素材。
