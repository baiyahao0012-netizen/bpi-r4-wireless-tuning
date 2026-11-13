# RTC over MAC 项目复核与重构路线

日期：2026-11-06  
复核对象：`bpi-r4-wireless-tuning` @ `1df6285`（与 `origin/main` 一致）  
重点材料：`_work_final/rtc/DELIVERY_20261106.md`、`RTC_OVER_WIFI_REPORT_20261105.md`、`RTC_LAYER_FUNCTION_AUDIT_20261105.html`，以及 `_work_final/rtc/` 下的核心代码。

---

## 0. 结论摘要

1. **当前项目证明的是“自定义实时媒体可以走以太网 L2，并经 AP 桥接到 Wi‑Fi”，不是“开源 RTC 协议可以跑在 MAC 层上”。**
2. **核心路线问题：前一个 Agent 把“去掉 UDP/IP”理解成了“重写一个更小的 RTC”，而不是“保留 RTC 核心、替换传输层”。** 因此做出来的是私有 RTC2，不是 RTP/RTCP/SRTP。
3. **下层 L2 传输是资产，上层 RTC2 是债务。** 审计已经说明：传输层本身质量代价很小，真正的问题在自定义 RTC 层的码率控制、反馈窗口、安全与互操作。
4. **正确的第一步不是继续补 RTC2，而是让开源 RTC 栈“以为自己在用一个 datagram socket”**：保留 RTP/RTCP/SRTP/编解码/抖动缓冲/GCC 原样，只把 UDP/IP 换成 L2 `PacketConn`。这样“不受影响的功能”是**按构造成立**的，不需要重写。
5. **受影响的功能再用适配层逐项打补丁**：编址/复用、MTU/分片、校验/完整性、NAT/ICE 替代、DTLS 传输、QoS/ECN、SDP 候选、OAM、浏览器互通。
6. **当前仓库可复用的是 L2 I/O、MAC 遥测、实验/测试资产，以及抖动/同步的算法参考；应淘汰的是 RTC2 的 28 字节线格式和自定义 EtherType/反馈帧。**
7. **公开前有硬阻断项**：仓库中有多处硬编码 SSH 凭据、无 LICENSE、无依赖清单、无 CI，且使用了 Npcap/FFmpeg/PyAV 等有许可证约束的组件。

---

## 1. 当前项目实际做了什么

### 1.1 实际架构

| 面 | 当前实现 | 证据 |
|---|---|---|
| 媒体面 | 以太网 II 裸帧，EtherType `0x88B5`；发送端从以太网口发出，经 BPI‑R4 `br-lan` 桥接到 Wi‑Fi；接收端在 Wi‑Fi 网卡上抓包 | `DELIVERY_20261106.md` 第 2.1 节；`txport.py`、`l2sock.py` |
| 协议 | 自定义 RTC2：28 B 头 + 帧级分片 + XOR FEC + 自定义 NACK/PLI | `rtc2.py` |
| 反馈 | 有线以太网发送；不是 Wi‑Fi 空口回传 | `DELIVERY_20261106.md` 第 2.1 节；`RTC_LAYER_HANDOFF_20261104.md` 第 2.3/5.2 节 |
| 控制/遥测 | 板端 `mac_agent.sh` 通过 TCP 上报 AQL、per‑STA airtime、重传等 | `mac_agent.sh`、`sender.py` 的 `_mac_listener` |
| 连接建立 | 静态 MAC 地址，无发现、无协商、无多客户端 | `sender.py --dst/--src`、`receiver.py --fb-*` |
| 安全 | 明文；无 SRTP、无 DTLS、无 802.1X/MACsec | 全仓库无加密路径 |
| 恢复 | 自定义帧内 XOR FEC、NACK 重传、PLI | `rtc2.py`、`receiver.py` |
| 抖动/同步 | 自定义 `PlayoutClock`/`PlayQueue`，共享播放时钟 | `receiver.py` |
| 拥塞控制 | 自定义 `Gcc` + AP 侧 MAC 埋点；ABR 默认关闭 | `sender.py` |

### 1.2 三个“不是”

**（1）不是 802.11 MAC 层。**

`l2sock.py` 用的是 Npcap 的 Ethernet 注入/捕获；代码里没有 802.11 MAC 头、TXOP、EDCA、A‑MPDU 或块确认的处理。发送端发的是 Ethernet II 帧，AP 负责桥接到 802.11。接收端在 Wi‑Fi 网卡上看到的仍是 AP 解封装后的 Ethernet 帧。  
所以准确说法是：**Ethernet L2 + AP bridge，最后一跳是 Wi‑Fi**，不是“端到端 802.11 MAC”。

**（2）不是完整的双向 RTC。**

媒体是单向 L2；反馈走有线；控制/遥测走 TCP；没有反向媒体、没有双向 SRTP、没有会话协商。它能证明“单向实时媒体可在 L2 上传输”，不能证明“RTC 会话可在 MAC 上建立和维持”。

**（3）不是开源 RTC 协议实现。**

没有 RTP/RTCP、没有 SRTP、没有 SDP、没有 ICE/DTLS；`webrtc_peer.py` 只是 aiortc 对照组，没有接入 L2 数据通路。RTC2 是私有协议，无法与任何标准端点互通。

### 1.3 哪些结论成立，哪些被高估

| 说法 | 判定 | 依据 |
|---|---|---|
| L2 可以承载实时音视频 | **成立** | 干净链路分片/重组/解码正常；`RTC_LAYER_AB_RESULTS_V2` 两臂帧数/解码率接近 |
| FEC/NACK/PLI 有效 | **在自定义协议内成立** | 注入丢包后恢复；但线格式不是标准 RTCP/RTX/FEC |
| 抖动缓冲/音视频同步有效 | **成立（受控条件）** | p50 16.7 ms、p95 27.5 ms；共享时钟设计合理 |
| “RTC 层功能一个都没少” | **高估** | 只覆盖分片/重组/抖动/解码/反馈；缺 RTP/RTCP/SRTP/SDP/DTLS/ICE；ABR 审计 P0 |
| “干净链路零丢帧” | **有上下文** | 干净链路 + FEC/NACK + 受控码率；20% 丢包下审计帧丢失 21.8% |
| “每包省 12 B” | **对比不对等** | 28 B 自定义头未含 SRTP；标准是 RTP+SRTP+UDP/IP 对比 RTP+SRTP+L2 shim |
| “MAC 感知 GCC 是核心差异化” | **方向有价值，当前证据不足** | `share/attr` 是 AP 侧信号；`iw station dump` 饱和时阻塞 4–5 s；降码率分支未复测 |
| “加密 1.5 天、连接建立 2 天” | **明显乐观** | 缺 DTLS/SDP/ICE/802.1X/密钥管理/多客户端；实验室 PSK 与产品级是两件事 |

---

## 2. 代码级复核

### 2.1 关键文件与职责

| 文件 | 实际职责 | 对目标的价值 |
|---|---|---|
| `rtc2.py` | 28 B 自定义头、分片、XOR FEC、NACK/PLI、时钟同步 | 低；线格式应淘汰，语义可作测试参考 |
| `txport.py` | `l2`/`udp` 两种传输，固定 EtherType，反馈/控制通道 | 高；可提炼为 `DatagramTransport` 接口 |
| `l2sock.py` | Windows Npcap 原始以太网收发 | 高（实验）；生产需 AF_PACKET/AF_XDP |
| `sender.py` | PyAV 采集/编码、RTC2 分片、FEC、缓存、GCC、MAC 控制 | 中；媒体 I/O 可复用，RTC 部分应替换 |
| `receiver.py` | RTC2 重组、FEC/NACK、抖动缓冲、解码、播放 | 中；播放时钟可参考，重组/反馈应替换 |
| `mac_agent.sh` | AP 侧 AQL/airtime/重传/PHY 采集，TCP 上报 | 高（Wi‑Fi AP 场景）；需重构为独立遥测服务 |
| `webrtc_peer.py` | aiortc 标准 WebRTC 对照组 | 高；作为互操作/行为基线，不作为实现底座 |
| `RTC_LAYER_FUNCTION_AUDIT_20261105.html` | 对 L2/UDP 两臂的逐项实测与 P0/P1/P2 问题清单 | 高；直接转成回归测试用例 |

### 2.2 已确认的代码/设计问题

| # | 问题 | 影响 |
|---|---|---|
| 1 | `rtc2.py` 没有版本、flow_id、TTL、头校验/完整性字段 | 多会话、环路保护、头篡改都无法处理 |
| 2 | 固定 EtherType `0x88B5/0x88B6/0x88B7` | 多会话/多流无法复用；实验性 EtherType 不适合出货 |
| 3 | 16 位 `seq`、32 位 `pts`/`send_ts_us` | 长时运行需要回绕处理；`pts` 90 kHz 约 13.25 h 回绕 |
| 4 | 无 SRTP/DTLS/身份认证 | 明文、可注入、可窃听；不能称为可部署 RTC |
| 5 | 反馈窗口 50 ms，15 fps 下不足 1 帧 | 单帧丢失即 500‰，审计已复现 `loss=50.0%` 与 `loss=0/1000` 矛盾 |
| 6 | ABR 每次调档重开编码器并强制 IDR | 审计 P0：15 s 内 16 次切换、14 次降档，解码帧 −18.4%，时延 p95 +342 ms |
| 7 | `share/attr` 依赖 AP 侧 `iw station dump` | 端点不可见；饱和时阻塞 4–5 s；不是通用 MAC 信号 |
| 8 | `attr` 用全局 `sent_chunks * chunk` 估算视频占用 | 音频/重传/头开销混入，归因可能偏差 |
| 9 | Npcap 用户态路径 | 审计：中位 +5.6 ms、p95 +39.6 ms；L2 抖动缓冲比 UDP 深 17 ms |
| 10 | 硬编码 MAC/IP/网卡名 | 不可移植；多环境复现困难 |
| 11 | 多个被跟踪脚本硬编码 SSH 用户名/密码 | 公开仓库会直接泄露凭据；必须轮换并清理历史 |
| 12 | 无 LICENSE、无 requirements/pyproject、无 CI | 不能作为开源项目交付 |
| 13 | 文档范围前后冲突 | 11‑04 handoff 写“仅限 RTC 层，不涉及 MAC 调优”；11‑06 delivery 又把 MAC 感知码率控制列为核心差异化。评审口径不统一 |

> 说明：审计的样本量 n=2/3、部分实验同机收发、反馈走有线，结论应视为“方向性证据”，不是最终定论。但它足以否定“RTC 层已经完整”的说法。

---

## 3. 与开源 RTC 协议的功能对照

### 3.1 判定原则

把 RTC 栈切成两段：

```text
┌──────────────────────────────────────────────┐
│ RTC 核心（不受 UDP/IP 影响）                  │
│  codec / RTP / RTCP / SRTP / jitter / A/V     │
│  FEC / NACK / PLI / GCC / SDP 内容            │
├──────────────────────────────────────────────┤
│ L2 适配层（受 UDP/IP 影响，需要补丁）          │
│  addressing / mux / MTU / checksum / QoS      │
│  discovery / DTLS transport / SDP candidate   │
│  OAM / interop                                │
├──────────────────────────────────────────────┤
│ Ethernet MAC / VLAN / Wi‑Fi bridge            │
└──────────────────────────────────────────────┘
```

**判断标准：这个功能是否直接依赖 IP 地址、UDP 端口、NAT、IP 分片、DSCP/ECN、ICMP。**  
不依赖的，原样复用；依赖的，写适配层。不要重写整个 RTC。

### 3.2 不受影响、应原样复用的功能

| 功能 | 标准/开源参考 | 为什么不受影响 | 当前项目 | 复用结论 |
|---|---|---|---|---|
| H.264/Opus 编解码 | RFC 6184 / RFC 7587；PyAV/FFmpeg | 编解码只看码流，不看 IP | `sender.py`/`receiver.py` 的 PyAV | PoC 可复用；生产换硬件/平台 |
| RTP 打包/解包 | RFC 3550、6184、7587 | RTP 只要求 datagram 边界 | 无，RTC2 替代 | **必须用标准 RTP** |
| RTCP SR/RR/SDES/BYE/XR | RFC 3550 | 只要求 datagram | 无，FBK1 替代 | **必须用标准 RTCP** |
| NACK/PLI/FIR | RFC 4585/5104 | 只是反馈报文 | 自定义 `NAC1`/`PLI1` | 语义可参考，线格式淘汰 |
| FEC/RTX | RFC 8627/4588 | 包级恢复，不依赖 IP | 自定义 XOR | 概念可参考，改用标准 |
| 抖动缓冲 | 开源 `rtpjitterbuffer` 等 | 只看到达时间/序号 | `PlayoutClock`/`PlayQueue` | 算法参考；生产用标准实现 |
| 音视频同步 | RTCP SR/NTP | 只看时间戳映射 | 共享播放时钟 | 设计可参考；改为 RTP/RTCP 时间轴 |
| SRTP 加密/认证 | RFC 3711 | 只保护 RTP/RTCP 载荷 | 无 | **必须补** |
| GCC/transport‑cc | 开源 WebRTC 实现 | 控制律只看延迟/丢包 | 自定义 `Gcc` | 可作实验对照；生产用标准 |
| Pacing | 开源实现 | 不依赖 IP | `Pacer` | 概念可复用 |
| SDP 编解码协商 | RFC 8866 | `rtpmap/fmtp` 与 IP 无关 | 无 | 用标准 SDP 子集 |
| DataChannel/SCTP | RFC 8831/4960 | 协议本身不依赖 IP | 无 | 后续可选 |
| 采集/渲染 | PyAV/sounddevice | 与网络无关 | `sender.py`/`receiver.py` | PoC 可复用 |

### 3.3 受影响、需要补丁的功能

| 功能 | 受影响点 | 补丁 |
|---|---|---|
| 编址/路由 | 没有 IP 地址/子网/路由器 | MAC + VLAN；L2 发现；跨网用网关 |
| 端口/五元组复用 | 没有端口，无法用五元组分流 | `flow_id` + EtherType + RTCP mux/BUNDLE |
| NAT/ICE/STUN/TURN | 没有 NAT，candidate 失效 | 删除 ICE；L2 发现/静态 peer；SDP L2 profile |
| MTU/PMTUD/分片 | 没有路径 MTU 发现和 IP 分片 | RTP 包 ≤ 1200 B；控制/DTLS 应用层分片 |
| UDP checksum | 没有端到端校验 | SRTP auth tag + L2 头 HMAC/CRC |
| QoS/ECN | 没有 DSCP/ECN | 802.1p PCP、WMM；MAC 遥测；无 ECN |
| DTLS 传输 | DTLS 原本跑在 UDP 上 | DTLS-over-L2 或 PSK/证书引导 SRTP |
| SDP 连接行/候选 | `c=`/`m=`/candidate 都是 IP | SDP L2 profile：MAC/flow_id/MTU |
| 发现/会话 | 没有 DHCP/DNS/mDNS | LLDP + 自定义 hello/offer；802.1X |
| OAM | 没有 ICMP/traceroute | LLDP/CFM/Y.1731；端口镜像；计数器 |
| 浏览器互通 | 浏览器不能发原始 L2 帧 | L2↔WebRTC 网关 |
| 安全边界 | 没有 IPsec | MACsec（逐跳）+ SRTP（端到端）+ 802.1X |
| 拥塞反馈路径 | 没有 ECN；反馈也要走 L2 | RTCP 反馈 + MAC 遥测；pacing |

### 3.4 当前项目对应物与复用结论

| 当前资产 | 类型 | 对目标的价值 | 处理建议 |
|---|---|---|---|
| `l2sock.py` | 原始 L2 I/O | **高**：可直接做 Windows 实验后端 | 移入 `transport/win_pcap`，补 MTU/错误/BPF 过滤 |
| `txport.py` | 传输抽象 | **高**：接口思想正确 | 重写为 `DatagramTransport`，去掉 RTC2 常量 |
| `rtc2.py` | 自定义协议 | **低**：线格式不兼容 | 归档 `legacy/`；提取 NACK/FEC/PLI 测试用例 |
| `sender.py` 采集/编码 | 媒体 I/O | **中**：PoC 可用 | 拆出 `media/`；RTC 部分替换 |
| `receiver.py` 解码/播放 | 媒体 I/O | **中**：PoC 可用 | 拆出 `media/`；重组/反馈替换 |
| `PlayoutClock`/`PlayQueue` | 抖动/同步 | **中高**：算法参考 | 作为 reference/回归对照；生产用标准 jitter buffer |
| `Gcc`/`Pacer` | 拥塞/节奏 | **中**：实验对照 | 放 `experiments/`；标准 GCC 为主 |
| `mac_agent.sh` + `_mac_ctrl` | MAC 遥测/归因 | **高（仅 Wi‑Fi AP 场景）** | 独立服务；JSON/共享内存；1 Hz 采样 |
| `bench*.py`/`sweep*`/`long_run` | 实验/回归 | **高** | 移入 `test/`，改标准 RTP/RTCP 指标 |
| `webrtc_peer.py` | aiortc 基线 | **高**：oracle/互操作 | 作为对照，不作为底座 |
| `RTC_LAYER_FUNCTION_AUDIT` | 审计数据 | **高**：失败模式/测试用例 | 转成自动化回归 |
| 早期 C 版 L2 demo | 原型 | **低** | 归档，保留接口经验 |

---

## 4. 当前仓库可复用的四类资产

### A. 直接复用（工程资产）

1. **`l2sock.py` + `txport.py` 的 L2 通路**：已验证 Ethernet 注入/捕获、方向过滤、非阻塞收包、最小帧填充处理。
2. **`mac_agent.sh` + MAC 遥测**：AQL、per‑STA airtime、retry/failed、PHY rate；`share/attr` 归因是项目里最有研究价值的部分。
3. **测试/实验脚本**：`bench*.py`、`sweep_jb*`、`long_run`、`clock_ab`、`verify_recv`、`an_pcm` 等，能快速搭回归。
4. **`webrtc_peer.py`**：标准 aiortc 对照，可直接作为“开源 RTC 栈行为基线”。

### B. 改造复用（算法/思想）

1. **`PlayoutClock`/`PlayQueue` 的共享播放时钟**：音视频共用 `tmin`/`D` 的思想正确，可移植到 RTP 时间戳 + RTCP SR。
2. **FEC/NACK/PLI 的恢复策略**：帧内 XOR、末片确认、15 ms 兜底、每缺口只请求一次；这些经验可用于标准 ULPFEC/RTX/RTCP 的参数调优。
3. **`Gcc`/`Pacer`**：作为对照/实验控制器，不作为生产实现；标准 GCC 的输入输出接口更值得复用。
4. **MAC 归因指标**：`share`/`attr` 可改造成 `CongestionSignalProvider`，但需解决 AP 依赖、采样慢、全局计数混入等问题。

### C. 应淘汰（协议/线格式）

1. RTC2 28 B 头、`magic/type/flags/stream_id/chunk_idx/chunk_cnt/frame_id/pts/send_ts_us` 的私有语义。
2. 固定 EtherType `0x88B5/0x88B6/0x88B7` 和 `FBK1/NAC1/PLI1/SYN1/SYN2` 自定义报文。
3. 自定义 `SeqGen`、按帧分片、按帧 XOR FEC 的线格式。
4. 自建“RTP 替代品”的路线本身。

### D. 完全缺失（必须补）

1. RTP/RTCP 标准栈与互通。
2. SRTP/DTLS/密钥管理/身份认证。
3. SDP/offer‑answer/能力协商。
4. 标准 NACK/RTX/PLI/FEC。
5. 标准 GCC/transport‑cc 与 RTCP 反馈。
6. L2 发现、多客户端、flow 管理。
7. MTU/分片/校验/头完整性。
8. QoS/ECN 替代、OAM、网关。

---

## 5. 正确的第一阶段：透明 L2 传输 + 标准 RTC 核心

### 5.1 架构

```text
┌─────────────────────────────────────────────┐
│ Media: H.264 / Opus                         │  原样
│ RTP / RTCP: SR/RR, NACK/PLI, transport-cc   │  原样
│ SRTP: AES-GCM, replay                       │  原样
├─────────────────────────────────────────────┤
│ L2 Adaptation Layer（新增）                  │  只改这里
│  flow_id / EtherType / RTCP mux             │
│  MTU / fragmentation / TTL / header HMAC    │
│  PCP/WMM QoS / discovery / DTLS-over-L2     │
│  SDP L2 profile / OAM                       │
├─────────────────────────────────────────────┤
│ Ethernet MAC / VLAN / Wi-Fi bridge          │
└─────────────────────────────────────────────┘
```

### 5.2 第一条 vertical slice

**不要一开始做视频 + 音频 + 拥塞控制 + 加密 + 多客户端。** 先做：

```text
Opus → RTP (RFC 7587) → SRTP (lab PSK) → L2 shim
     → Ethernet → 反向 RTCP RR/NACK/PLI
     → jitter buffer → Opus 解码/播放
```

验收：Wireshark 能按标准 RTP/RTCP 解析；无 IP 头；SRTP 能解密；抖动缓冲能处理乱序/重复/丢失；播放间隔稳定。

然后按顺序加：

1. H.264 RTP（RFC 6184，单 NAL/FU‑A/STAP‑A）。
2. RTCP SR + 音视频同步。
3. NACK/RTX/PLI + FEC。
4. GCC/transport‑cc + pacing。
5. SRTP/DTLS/802.1X。
6. SDP/发现/多客户端。
7. 网关/浏览器互通。

### 5.3 为什么不是继续扩展 RTC2

- 每加一个标准能力（SRTP、RTCP、SDP、DTLS、互通），都要再发明一套私有协议。
- 现有 RTC2 已经出现反馈窗口、ABR、头完整性、长时回绕等问题；继续扩展会把问题叠加。
- 标准 RTP/RTCP/SRTP 有成熟实现、抓包工具、互通测试和 20 年工程验证；没有理由重写。
- **“不受影响的功能”最完整的复现方式，就是不要碰它们。**

### 5.4 技术选型

| 方案 | 优点 | 缺点 | 建议 |
|---|---|---|---|
| **GStreamer** | `rtpbin`/`rtpjitterbuffer`/`srtp`/`rtpulpfec`/`rtx` 现成；C，板端友好；LGPL | 需要写自定义 `GstBaseSrc/Sink`；无完整 WebRTC/ICE | **第一阶段首选** |
| **Pion** | MIT；`rtp`/`rtcp`/`srtp` 模块化；Go 易交叉编译 | 需要自己组装 jitter/interceptor；无浏览器 API | 协议核心备选 |
| **aiortc** | Python；与现有代码同栈；易做对照 | 自定义传输不便；性能有限 | **只做 oracle/对照** |
| **libwebrtc** | 完整 WebRTC/媒体引擎 | 网络层与 ICE/UDP 耦合深，替换成本极高 | 不首先 fork；要浏览器互通优先用网关 |

**推荐：GStreamer 做标准 RTP/RTCP/SRTP/ jitter 的承载；aiortc 做行为对照；Pion 作为后续可编程协议核心的备选。**

### 5.5 `DatagramTransport` 接口

```text
ReadFrom(p) -> (n, Addr)       # 保留 datagram 边界
WriteTo(p, Addr) -> n          # 不重组、不重传
LocalAddr() -> Addr
MTU() -> int                   # 例如 1200
SetReadDeadline(t)
SetPCP(v) / SetWMM(ac)         # QoS
Close()
```

`Addr` 不是 IP/port，而是：

```text
{ mac: 6 bytes, flow_id: 16/32 bits, vlan: optional }
```

约定：

- `WriteTo` 超过 MTU 返回 `ErrMessageTooLong`，由上层 RTP 打包/控制分片处理。
- 传输层不保证顺序/不重传；RTP/RTCP 自己处理。
- 头校验/加密在 shim 或 SRTP 层完成；不要依赖 Ethernet FCS。
- 任何 `flow_id` 都必须能映射到会话/SSRC/MID，避免只靠 MAC 做身份。

### 5.6 第一阶段验收标准

| # | 验收项 | 方法 |
|---|---|---|
| 1 | RTP/RTCP 线格式正确 | Wireshark 解析；与 RFC 样例对比 |
| 2 | 无 IP/UDP 头 | pcap 检查 EtherType/偏移 |
| 3 | SRTP 加解密/重放保护 | 错误 key/重放包必须失败 |
| 4 | 抖动缓冲 | 乱序/重复/丢失注入；p95 出队间隔 |
| 5 | A/V 同步 | RTCP SR；p95 ≤ 40 ms（干净链路） |
| 6 | NACK/PLI/RTX/FEC | 丢包注入；恢复率/解码率 |
| 7 | MTU | 无帧 > 1500；RTP 包 ≤ 1200；无 IP 分片 |
| 8 | GCC | 丢包/时延阶跃；无持续震荡 |
| 9 | 互操作 | 标准 RTP 工具/网关能收 |
| 10 | 回归 | 与 UDP/IP 基线逐项对比 |

---

## 6. 第二阶段：受影响功能的补丁清单

| # | 补丁 | 责任 | 关键设计 | 验收 |
|---|---|---|---|---|
| 1 | `AddressingAdapter` | MAC/VLAN/flow_id | 不用 MAC 做身份；证书/Device ID；VLAN 隔离 | 多设备不串流 |
| 2 | `MultiplexAdapter` | flow_id + EtherType + RTCP mux | 一个会话一个 flow；BUNDLE 用 MID/RID；RTCP 按类型分流 | 音视频/RTCP 不混淆 |
| 3 | `MtuAdapter` | RTP 包 ≤ 1200；控制分片 | H.264 FU‑A；DTLS 分片；重组超时 | 无 IP 分片；大帧可过 |
| 4 | `IntegrityAdapter` | 头完整性 | SRTP auth tag + shim HMAC；防重放 | 篡改头被拒 |
| 5 | `DiscoveryAdapter` | L2 发现 | LLDP 拓扑 + 自定义 hello/offer；小规模静态 | 设备可发现/可配对 |
| 6 | `SecurityAdapter` | DTLS-over-L2/PSK | DTLS 1.3 或 PSK；802.1X；密钥轮换 | 无明文；密钥可轮换 |
| 7 | `SdpAdapter` | SDP L2 profile | 保留 `m=`/`rtpmap`/`fmtp`/`rtcp-mux`/`fingerprint`；替换 `c=`/候选 | offer/answer 可互通 |
| 8 | `QosAdapter` | PCP/WMM | 音频 AC_VO、视频 AC_VI；无 ECN | 优先级可测 |
| 9 | `CongestionAdapter` | GCC + MAC 遥测 | RTCP transport‑cc 为主；`share/attr` 为辅；无 ECN | 不误判外部拥塞 |
| 10 | `OamAdapter` | LLDP/CFM | 无 ICMP；端口镜像；计数器 | 可定位故障 |
| 11 | `InteropAdapter` | L2↔WebRTC 网关 | SRTP 终结/重签；ICE/DTLS；转码 | 浏览器可看 |

**优先级：** 1–4 是媒体可用性；5–7 是会话/安全；8–9 是性能；10–11 是运维/互通。

---

## 7. 仓库与开源工程化建议

### 7.1 仓库重构

```text
rtc-over-mac/
  core/                 # GStreamer/Pion 标准 RTP/RTCP/SRTP
  transport/
    l2_packetconn/      # Windows Npcap / Linux AF_PACKET / macOS BPF
    shim/               # EtherType, flow_id, MTU, TTL, HMAC
  session/              # discovery, SDP L2 profile, peer table
  security/             # DTLS-over-L2, PSK, 802.1X, key rotation
  qos/                  # PCP/WMM, pacing, MAC telemetry
  app/                  # send/recv, media I/O
  test/
    conformance/        # RFC vectors, pcap, Wireshark
    impairment/         # loss/reorder/dup/MTU/loop
    interop/            # aiortc/browser gateway
  legacy/rtc2/          # v0.6.10, 只读归档
  docs/
```

### 7.2 开源阻断项（必须先处理）

| # | 阻断项 | 说明 |
|---|---|---|
| 1 | **硬编码 SSH 凭据** | 至少 8 个被跟踪脚本含同一组用户名/密码；公开前必须轮换、改环境变量/SSH key，并清理 git 历史 |
| 2 | **无 LICENSE** | 仓库根目录没有 LICENSE；需明确代码/文档/数据的许可 |
| 3 | **依赖许可证** | Npcap（OEM 许可）、FFmpeg/PyAV（LGPL/GPL）、aiortc、GStreamer（LGPL）、H.264/AAC 专利 |
| 4 | **无依赖清单/CI** | 无 `requirements.txt`/`pyproject.toml`；手动脚本不可复现 |
| 5 | **硬编码 MAC/IP/SSID/网卡名** | 不可移植；需配置文件/环境变量 |
| 6 | **大文件/日志/测试视频** | 仓库含大量二进制/日志；建议 LFS 或 artifact |
| 7 | **文档编码/版本** | `CHANGELOG.md` 存在乱码；需统一 UTF‑8，补协议版本 |
| 8 | **无安全设计** | 明文、无认证；开源前至少加 SRTP/DTLS/威胁模型 |

> 如果仓库要公开，先做一次 `git filter-repo`/BFG 清理凭据历史；仅删除当前文件不够。

### 7.3 建议的测试矩阵

| 类别 | 用例 |
|---|---|
| 线格式 | RTP/RTCP 头、扩展、padding、compound、rtcp‑mux |
| 丢包 | 随机、突发、尾片丢失、连续丢包、FEC 边界 |
| 乱序/重复 | 1–100 包乱序、重复包、迟到包 |
| MTU | 1200/1500、最大帧、控制报文分片、超时重组 |
| 抖动 | 固定/突发/正弦、Wi‑Fi 重传模型 |
| 安全 | 错误 key、重放、篡改头、降级、密钥轮换 |
| QoS | PCP/WMM 映射、拥塞、PFC/PAUSE 影响 |
| 拓扑 | 单交换机、跨交换机、VLAN、环路、LAG |
| 互操作 | aiortc、浏览器网关、标准 RTP 工具 |
| 长时 | 2 h/24 h、序号/时间戳回绕、内存/句柄泄漏 |

---

## 8. 里程碑与估时

| 里程碑 | 内容 | 粗略估时 |
|---|---|---|
| M0 | 冻结 v0.6.10，归档 RTC2；建新分支/目录 | 0.5 天 |
| M1 | 标准 RTP/RTCP/SRTP over UDP 基线 + 一致性测试 | 3–5 天 |
| M2 | `L2PacketConn` + Opus RTP over L2（静态 peer、PSK） | 3–5 天 |
| M3 | H.264 RTP + jitter + RTCP SR + A/V sync | 5–7 天 |
| M4 | NACK/RTX/PLI/FEC + 丢包测试 | 3–5 天 |
| M5 | SRTP/DTLS/802.1X/密钥管理 | 5–10 天 |
| M6 | SDP L2 profile + 发现 + 多客户端 | 5–10 天 |
| M7 | GCC/transport‑cc + MAC 遥测/QoS | 5–10 天 |
| M8 | 网关/浏览器互通/长时/运维 | 5–10 天 |

**总计约 6–10 周（小团队、已有媒体/网络经验）。** 这比交付文档里“加密 1.5 天、连接建立 2 天”现实得多；后者最多只能算“实验室 PSK + 静态 MAC”的 PoC。

---

## 9. 需要确认的问题

1. **目标链路**：有线 Ethernet、Wi‑Fi（经 AP 桥接），还是真正的 802.11 MAC 注入？三者难度完全不同。
2. **是否要浏览器/远端互通**？如果要，纯 L2 只能到边缘，必须有 WebRTC 网关。
3. **单向还是双向**？是否需要多客户端/多会话？当前项目只有单向媒体 + 带外反馈。
4. **安全等级**：实验室 PSK 即可，还是必须 DTLS‑SRTP + 802.1X + MACsec？
5. **团队技术栈**：Python、C/C++、Go？这决定 GStreamer/Pion/aiortc 的选择。
6. **“Mac”到底指 MAC 层还是 macOS？** 如果是 macOS，原始 L2 注入只能走 BPF/root，Wi‑Fi 基本不可行。

---

## 10. 一句话建议

**保留当前项目的 L2 传输、MAC 遥测和实验资产；停止扩展 RTC2；用开源 RTP/RTCP/SRTP 栈做“透明 L2 传输”，先把不受影响的功能原样跑通，再逐项补受影响的功能。**  
这不是推翻现有工作，而是把“自定义 RTC”换成“标准 RTC + L2 适配层”，让已有实验数据真正服务于一个可互通、可验证、可开源的 RTC over MAC 实现。

---

## 11. 应用场景修正：STA → AP 上行视频

### 11.1 场景

```text
Camera / STA ──802.11 上行──▶ AP（开发板，接收端）
                                  │
                                  ├── 有线 Ethernet：SSH / 抓包 / 导出 H.264
                                  └── L2 反馈/控制 ──▶ STA
```

- 视频从 STA 上行到 AP；**AP 开发板就是接收端**，不再经过算力平台。
- 有线口只承担管理、抓包、把 H.264/统计导出到 PC 做离线分析；它不是媒体主链路。
- 不要求高帧率，但要求高画质；目前先做视频，后续加音频与音视频同步。
- 局域网内，无公网、无 NAT。

这更像“**无线高画质视频上行到 AP 端**”，不是双向会议 RTC，也不是“AP 再转发给算力平台”。

### 11.2 与当前项目的三处关键差异

1. **方向相反。** 当前项目是“有线发送端 → AP → Wi‑Fi 接收端”的下行；目标场景是“Wi‑Fi STA → AP → 有线算力”的上行。当前 `mac_agent.sh` 的 `tx duration` 是 AP 下行发送时间，不能直接代表 STA 上行空口占用；`share/attr` 的语义要翻转。
2. **AP 是天然的反馈注入点。** 当前项目受限于“Windows Wi‑Fi 不能注入”，只能走有线反馈；在目标场景里，AP 本身是 Linux/OpenWrt，可以直接向 STA 发送 802.11/L2 反馈帧。**这反而比当前项目更容易做闭环。**
3. **优化目标从“低时延”变成“高画质 + 有界时延 + 帧完整性”。** 低帧率、高画质意味着单帧更大、突发更强、丢一个分片就可能毁整帧；当前面向 2.5 Mbps 会话视频的 16 位序号、单 XOR 校验、40–200 ms 抖动缓冲不够用。

### 11.3 高画质低帧率带来的定量问题

| 场景 | 单帧大小（约） | 1200 B 分片数 | 0.1% 丢包下的整帧丢失率 |
|---|---:|---:|---:|
| 1080p 10 fps 20 Mbps | 250 KB | ~208 | ~18.8% |
| 4K 10 fps 50 Mbps | 625 KB | ~533 | ~41.3% |
| 4K 10 fps 100 Mbps | 1.25 MB | ~1042 | ~64.7% |

公式：`1 - (1 - p)^N`。这意味着：

- **高画质场景对丢包极其敏感**；0.1% 的包丢失就可能让 40%–65% 的帧不完整。
- 802.11 MAC 重传能降低有效丢包，但不能消除；突发丢包更糟。
- 必须把 **FEC/ARQ/帧级完整性** 放在第一位，而不是只做码率自适应。
- 16 位 RTP 序号在 10k pps 下约 6.5 s 回绕；标准 RTP 用 ROC/扩展序号处理，自定义 RTC2 没有这套机制。
- 50 Mbps 下 625 KB 单帧的空口发送时间约 100 ms；叠加抖动缓冲、重传、AP 排队，端到端时延预算要重新算。

### 11.4 这个场景下 RTC 层该保留什么

**仍然保留：**

- RTP/RTCP/SRTP：标准包格式、扩展序号、RTCP RR/SR、NACK/RTX/PLI、transport‑cc。
- 抖动缓冲：但目标不是 40 ms，而是 100–300 ms 的“有界画质缓冲”，按帧截止时间丢弃过期帧。
- 帧级 FEC/ARQ：ULPFEC/FlexFEC + NACK/RTX；大帧需要更强的 FEC 或分块 ARQ。
- GCC/pacing：但输入要改成 **STA 上行队列 + AP 上行空口遥测**，不是当前 AP 下行 `tx duration`。
- SRTP/DTLS/802.1X：局域网也必须加密/认证。

**可以弱化或去掉：**

- ICE/STUN/TURN：局域网、AP 已知 STA，不需要 NAT 穿透。
- 音频 AEC/AGC/PLC：如果没有音频，不需要。
- 浏览器互通：AP 是自定义接收端，可以先不做网关；但保留标准 RTP 以便工具/未来互通。
-  conversational 低时延目标：不必追求 20–50 ms，重点是有界时延 + 帧完整性。

### 11.5 建议的目标架构

```text
STA（Linux/嵌入式相机）
  RTP/RTCP/SRTP + pacing + NACK/RTX/FEC
  WMM AC_VI / 上行队列遥测
        │ 802.11 uplink
        ▼
AP（BPI-R4 / OpenWrt，接收端）
  RTP/RTCP/SRTP receiver + jitter buffer
  UplinkTelemetry：per-STA RX airtime、channel busy、retry/duplicate、RSSI/MCS
  Feedback：RTCP RR/NACK/PLI → STA（AP 原生注入，优先 AC_VO）
        │ 有线 Ethernet（仅管理/抓包/导出）
        ▼
PC（可选）：离线解码、PSNR/SSIM/VMAF、日志分析
```

关键点：

- **AP 就是 RTC 接收端**，不是透明 bridge，也不需要算力平台参与媒体链路。
- **反馈是一段**：AP → STA，直接走 Wi‑Fi L2；不需要“算力平台 → AP → STA”的三段代理。
- **遥测方向要翻转**：当前 `mac_agent.sh` 的 `tx duration` 是 AP→STA 下行；目标场景需要 AP 侧 **RX airtime / channel busy**，以及 STA 侧 **TX queue/AQL**。
- **STA 必须是 Linux/嵌入式**才能做真正的“on MAC”；Windows 只能做“over Ethernet L2 + AP bridge”，无法控制 802.11 上行调度。
- 如果 AP 的 CPU/存储不适合跑完整 RTP/SRTP/解码，第一轮可以让 AP 只做 L2 抓包/桥接，由有线 PC 做临时接收端；但**协议验证仍以 AP 为无线接收端**。

### 11.6 第一阶段（针对该场景）

不要先做双向音频/浏览器。先做：

```text
H.264/HEVC（高码率、低帧率）
  → RTP (RFC 6184)
  → SRTP (lab PSK)
  → L2 shim (flow_id, MTU 1200, TTL, header HMAC)
  → STA Wi-Fi uplink
  → AP 开发板：RTP/RTCP/SRTP receiver
  → jitter buffer + 存 H.264 / 统计
  → 有线口导出，PC 离线解码 + 质量评估
```

第一轮验收：

- 单 STA、单视频流、1080p/4K、10–15 fps、20–50 Mbps。
- 无 IP/UDP 头；标准 RTP/RTCP 可解析；SRTP 可解密。
- 注入 0.01%/0.1%/突发丢包，测整帧丢失率、NACK/RTX/FEC 恢复率、解码质量。
- 测 AP 上行 airtime/channel busy、STA TX queue、MCS/RSSI、端到端时延。
- 与 UDP/IP 基线对比，确认“去掉 IP/UDP”的收益不是靠牺牲画质/时延换来的。

第二轮再做：

1. AP 上行遥测 + 反馈代理。
2. 大帧 FEC/ARQ 策略（按帧截止时间）。
3. WMM/EDCA 上行优先级、A‑MPDU、OFDMA/MU‑MIMO。
4. 多 STA 公平性/准入控制。
5. “on MAC”：截止时间感知的重传上限、过期帧丢弃、AP 上行调度。

### 11.7 需要确认的场景参数

1. 分辨率/帧率/目标码率：1080p/4K/8K？10/15/30 fps？20/50/100 Mbps？
2. 端到端时延预算：100 ms、300 ms，还是 1 s？这决定 RTC 是否必要。
3. STA 数量：单相机还是多相机？是否需要公平性/准入控制？
4. STA 平台：Linux/嵌入式，还是 Windows？这决定能否做“on MAC”。
5. AP 型号/驱动：MT7996？能否加载自定义 agent/驱动补丁？
6. AP 资源：CPU/内存/存储/是否可装 GStreamer/Python/Go；1080p30 是否只存 H.264 还是需要实时解码？
7. 编码器：H.264/HEVC/AV1？硬件编码还是软件？是否接受 All‑Intra？
8. 是否有音频？是否需要音视频同步？
9. 有线口用途：只做 SSH/抓包，还是要把 H.264/统计导出到 PC 做离线分析？

---

## 12. 1080p30 视频-only 首测参数

### 12.1 码率与帧大小

1080p30（1920×1080@30）在“高画质”下建议先测 **10 / 15 / 20 Mbps** 三档 H.264 High Profile；HEVC 可在同画质下更低，但先不要同时换编码器。

| 目标码率 | 单帧大小（约） | 1200 B 分片数 | 0.1% 包丢失下整帧丢失率 |
|---:|---:|---:|---:|
| 10 Mbps | 41.7 KB | ~35 | ~3.4% |
| 15 Mbps | 62.5 KB | ~53 | ~5.2% |
| 20 Mbps | 83.3 KB | ~70 | ~6.8% |

结论：

- 1080p30 的帧比 4K/低帧率小，丢包放大没那么严重，适合作为第一条打通链路。
- 20 Mbps 已属于“高画质”档；再高要看 Wi‑Fi 上行余量和 AP 排队。
- 如果把帧率降到 15/10 fps 来换画质，同码率下单帧会翻倍/三倍，整帧丢失率反而上升；需要更强的 FEC/ARQ，不能只看“帧率低了更稳”。

### 12.2 第一轮只做视频，但按“未来有音频”设计

- 视频：H.264 High Profile，1080p30，10–20 Mbps，GOP 1–2 s，关闭 B 帧或固定短 B 帧，便于低延迟。
- 音频（后续）：Opus 48 kHz、20 ms、64–128 kbps；单独 SSRC；与视频共用 RTCP SR 时基。
- 协议：RTP/RTCP/SRTP；视频/音频用不同 SSRC，但同一个 L2 `flow_id`；RTCP mux。
- 同步：接收端用 RTCP SR 把 RTP 时间戳映射到共同墙钟；音频为主时钟，视频按需丢帧/重复；目标 p95 ≤ 40 ms。
- 注意：无 IP 不等于无时钟；RTCP SR 自带 NTP 时间戳，不需要 NTP 服务。

### 12.3 第一轮验收

| 项 | 目标 |
|---|---|
| 无 IP/UDP | pcap 中只有 EtherType + RTP/RTCP/SRTP |
| 标准解析 | Wireshark 能按 RTP/RTCP 解析 |
| 视频 | 1080p30，10/15/20 Mbps 各 60 s |
| 帧完整率 | 干净链路 ≥ 99.9%；0.1% 丢包下 ≥ 95%（靠 NACK/RTX/FEC） |
| 画质 | PSNR/SSIM/VMAF 不低于 UDP/IP 基线 |
| 时延 | 端到端 p95 先定 100–200 ms（按场景再收紧） |
| AP 侧 | 上行 airtime、channel busy、MCS/RSSI、retry/duplicate 可读 |
| STA 侧 | TX queue/AQL、发送重传、pacing 可读 |

### 12.4 建议的测试顺序

1. 1080p30 / 10 Mbps / 干净链路：先保证 RTP/RTCP/SRTP 与解码正确。
2. 1080p30 / 15 / 20 Mbps：看 AP 上行余量、排队、丢包。
3. 0.01% / 0.1% / 突发丢包：看整帧丢失率、NACK/RTX/FEC 恢复。
4. 1080p15 对比：同码率下画质提升 vs 帧丢失率上升。
5. 加 Opus 音频：A/V sync p95、音频丢包/PLC。
6. 加 AP 上行遥测/反馈代理：闭环码率/FEC。
7. 多 STA/长时间：公平性、回绕、内存/句柄。

---

## 13. STA 硬件选型：外加一台 Linux 设备

### 13.1 需求

- 能跑 Linux（Ubuntu/Debian），可 SSH 远控；
- 有 **有线 Ethernet + Wi-Fi** 两个接口：有线做 SSH/管理，Wi-Fi 做 STA 上行；
- Wi-Fi 支持 5 GHz、station 模式，能用 `AF_PACKET` 发自定义 EtherType；
- 能实时编码 1080p30 高画质（最好有硬件 H.264/HEVC 编码）；
- 功耗/体积/价格可接受；
- 后续可做“on MAC”的驱动级实验（加分项，不是第一阶段必需）。

### 13.2 候选对比

| 设备 | 1080p30 实时高画质 | Linux/远控 | Wi-Fi raw L2 | 难度/价格 | 结论 |
|---|---|---|---|---|---|
| **Intel N100/N305 迷你主机** | ✅ QSV 硬件编码，轻松 | ✅ Ubuntu | ✅ 内置/加 USB Wi‑Fi | 低/中 | **首选** |
| **二手 Intel 迷你主机**（M720q/800 G4 等） | ✅ QSV | ✅ | ✅ M.2 Wi‑Fi | 低/低 | 预算首选 |
| **Radxa Rock 5B / Orange Pi 5 Plus**（RK3588） | ✅ 硬件 H.264/HEVC | ✅ | ✅ M.2/USB Wi‑Fi | 中/中 | ARM/硬件编码备选 |
| **Raspberry Pi 5 8GB** | ⚠️ 软件编码，高画质可能吃力 | ✅ | ✅ brcmfmac + AF_PACKET | 低/低 | 预编码文件/协议验证可以，实时高画质不首选 |
| **Raspberry Pi 4** | ❌ 编码能力弱 | ✅ | ✅ | 低/低 | 不推荐做 1080p30 高画质 |
| **Jetson Orin Nano** | ✅ 硬件编码 | ✅ | ✅ | 高/高 | 后续带 AI 再考虑，当前过配 |
| **ESP32 / ESP32-P4** | ❌ 不是 Linux，1080p30 不现实 | ❌ | ⚠️ 可做 802.11 实验 | 低/低 | **不推荐** |

### 13.3 推荐配置

**首选：Intel N100/N305 迷你主机**

```text
CPU：Intel N100 / N305
内存：16 GB（8 GB 也可，16 GB 更稳）
存储：512 GB NVMe
网络：2.5G Ethernet + Wi‑Fi（AX210 / MT7922）
系统：Ubuntu 24.04 LTS
用途：SSH 管理走 Ethernet；媒体走 Wi‑Fi STA
```

理由：

- QSV 硬件编码 1080p30 H.264/HEVC 很轻松，画质/码率可控；
- Ubuntu 驱动成熟，GStreamer/FFmpeg/Python 工具齐全；
- 2.5G 有线 + Wi‑Fi 双接口，正好符合“管理走有线、媒体走 Wi‑Fi”；
- 比树莓派贵不了太多，但省掉编码性能这个变量。

**备选：Radxa Rock 5B / Orange Pi 5 Plus**

- RK3588 有硬件 H.264/HEVC 编码，1080p30 没问题；
- 需要 M.2/USB Wi‑Fi（建议 MT7922/MT7921AU）；
- Linux/MPP/GStreamer 配置比 x86 麻烦，适合想要 ARM /低功耗/后续嵌入式形态。

**预算/临时：Raspberry Pi 5 8GB**

- 适合先发**预编码 1080p30 H.264 文件**，验证 L2/RTP；
- 实时高画质编码可能掉帧；不要用它来证明“高画质实时编码”；
- Pi 4 不建议。

**不推荐：ESP32 系列**

- 不是 Linux，没有完整 RTP/RTCP/SRTP/GStreamer 生态；
- 1080p30 视频编码/传输不现实；
- 只适合做低层 802.11 帧实验/传感器，不适合本项目主线。

### 13.4 网络与远控

```text
Windows PC ──Ethernet──┐
                       ├── BPI-R4 AP（OpenWrt）
Linux STA ──Ethernet───┘        │
     │                          │
     └──── Wi-Fi 5G STA ────────┘
```

- Linux STA 的 **Ethernet** 接 AP 的 LAN，用于 SSH/管理/导出；
- Linux STA 的 **Wi‑Fi** 关联 AP 的 SSID，用于媒体上行；
- 不要让媒体帧绕回 Ethernet 形成环路；必要时用 VLAN/ebtables 隔离；
- SSH 用密钥，`tmux` 保持长任务；`tcpdump`/`iw`/`ethtool` 预装；
- 媒体 socket 绑定 Wi‑Fi 接口，SSH/路由走 Ethernet；注意路由 metric。

### 13.5 采购清单

- Intel N100/N305 迷你主机（16 GB/512 GB/2.5G Ethernet）；
- Wi‑Fi：优先内置 AX210/MT7922；没有则买 Linux 支持的 USB Wi‑Fi（MT7921AU 等）；
- 5 GHz 外置天线（如果网卡可换天线）；
- 12 V 电源、网线、HDMI 假负载/键盘（首次安装用）；
- 可选：USB 麦克风/音箱（后续音频）、智能插座（远程重启）。
