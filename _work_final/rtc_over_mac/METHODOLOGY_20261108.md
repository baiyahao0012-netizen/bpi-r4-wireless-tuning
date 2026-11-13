# RTC over MAC 两条实现路线评估

日期：2026-11-08  
对象：STA（Raspberry Pi 5 + MT7921AU）→ AP（BPI-R4）的 1080p 带音频上行  
素材：`_work_final/rtc/media/testset_1080p/` 六条 1080p24/25/30 带音频视频

---

## 0. 结论

**推荐思路 1，但必须限定范围：不是“实现完整 WebRTC”，而是“用开源组件实现最小 RTP/RTCP/SRTP 媒体面，先跑 UDP/IP，再换 L2”。**

更准确的说法是：

```text
先建立“标准 RTC 参考实现”
→ 再建立“同一套 RTC 代码 + 可切换传输”的双栈
→ 用差分测试找出 L2 带来的真实影响
→ 只裁剪确认不需要的
→ 只修复确认受影响的
```

**不要采用“直接上 L2、边做边补”的纯思路 2。** 当前项目已经验证过这条路的代价：做了 RTC2、自定义反馈、自定义 ABR，最后出现 P0 级码率控制问题，且无法与标准 RTP/RTCP 互通。

---

## 1. 两条路线对比

| 维度 | 思路 1：先 UDP/IP 基线，再换 L2 | 思路 2：直接 L2，边做边补 |
|---|---|---|
| 参考基准 | 有，标准 RTP/RTCP/SRTP 行为可测 | 无，只能靠猜 |
| 问题归因 | 能区分“RTC 功能缺失”与“L2 影响” | 两者混在一起，难定位 |
| 复用开源 | 高，先跑通现成栈 | 低，容易重写成私有协议 |
| 早期风险 | 可能 scope 过大（完整 WebRTC） | 早期就能看到 L2 通路 |
| 裁剪依据 | 有 baseline 数据，按证据裁剪 | 容易凭感觉裁错 |
| 回归测试 | 同一套测试跑两遍 | 没有对照，回归无意义 |
| 当前项目教训 | 未走这条路 | 已走，结果 RTC2/P0 |
| 适用性 | **推荐为主线** | 只适合极小原型/一次性验证 |

### 思路 1 的最大风险

不是“多走一步”，而是**把“开源 RTC”理解成完整 WebRTC**：

- ICE/STUN/TURN
- DTLS/SDP/DataChannel
- 浏览器 API
- simulcast/SVC/多方 SFU

这些对本场景大多不需要。  
所以思路 1 必须裁剪成：

```text
H.264 / Opus
+ RTP / RTCP
+ SRTP
+ jitter buffer
+ NACK/PLI/RTX/FEC
+ RTCP SR 音视频同步
+ GCC/pacing（第二阶段）
+ 最小 SDP profile
```

不是“把 libwebrtc 全搬过来”。

### 思路 2 的最大风险

不是“先做 L2”本身，而是：

- 没有 baseline，无法判断功能是否“复现完整”；
- 很容易把“RTP 的功能”重新发明成私有头/私有反馈；
- 裁剪发生在理解之前，容易裁掉后面音视频同步/安全/恢复需要的东西；
- 最终得到一个能跑、但不可互通、不可证明的私有协议。

当前项目的 RTC2 就是这条路的结果。

---

## 2. 推荐路线：基线优先 + 传输缝 + 差分驱动

### Phase 0：定义最小 profile

先写死本阶段范围：

| 项 | 选择 |
|---|---|
| 视频 | H.264 High，1080p24/25/30 |
| 音频 | Opus 48 kHz，立体声/单声道 |
| 传输 | RTP/RTCP over UDP/IP（baseline）→ over L2（target） |
| 安全 | SRTP；实验室先用 PSK，后续 DTLS |
| 会话 | 单 STA、单流、静态 peer；不做 ICE |
| 反馈 | RTCP RR、NACK、PLI；后续 transport-cc |
| 同步 | RTCP SR + 共享播放时钟 |
| 不做 | ICE/STUN/TURN、DataChannel、SVC、多方、浏览器 |

### Phase 1：UDP/IP 基线

用开源栈跑通：

```text
文件 → H.264/Opus → RTP → SRTP → UDP/IP → 接收端
```

要求：

- 同一套编码参数、同一 GOP、同一时间戳；
- 六条素材都能播；
- 音频 AAC 先转 Opus；
- 记录 RTP/RTCP pcap、帧完整率、抖动、A/V sync、码率、时延；
- 这份数据是后面的“标准答案”。

### Phase 2：加传输缝，不重写 RTC

从第一天就把传输抽象出来：

```text
RTP/RTCP/SRTP
      │
DatagramTransport
   ├── UDP/IP
   └── L2 (EtherType + flow_id + MTU + TTL + HMAC)
```

要求：

- 同一份 RTP/RTCP/SRTP 代码；
- 只替换 `send/recv`；
- 一个 `--transport udp|l2` 开关；
- 不要复制两份媒体代码。

这是整个方案的关键。  
**“不受影响的功能”不是复现出来的，而是因为没被碰过而保留下来的。**

### Phase 3：差分测试

同一素材、同一编码、同一接收端，分别跑 UDP 和 L2：

| 指标 | 目的 |
|---|---|
| RTP/RTCP 包格式 | 确认标准栈没被改坏 |
| 帧完整率/解码率 | 确认 L2 没有引入额外丢帧 |
| 抖动缓冲深度 | 确认 L2 的时延代价 |
| A/V sync p50/p95 | 确认音视频同步未受影响 |
| 端到端时延 | 确认 L2 的真实代价 |
| PSNR/SSIM/VMAF | 确认画质没有下降 |
| CPU/内存 | 确认 Pi 侧可承受 |

只把“L2 与 UDP 的差值”当作需要修复的对象。

### Phase 4：裁剪

顺序必须是：

1. **配置裁剪**：关闭 ICE/DataChannel/SVC/多方/浏览器；
2. **构建裁剪**：不编译不需要的模块；
3. **代码裁剪**：确认无回归后再删代码。

不要一上来删源码。  
每一刀都要有 baseline 对照。

### Phase 5：修复受影响功能

| 受影响功能 | 修复 |
|---|---|
| 端口/五元组复用 | `flow_id` + EtherType + RTCP mux |
| MTU/分片 | RTP 包 ≤ 1200；控制/DTLS 应用层分片 |
| UDP checksum | SRTP auth tag + L2 头 HMAC |
| ICE/NAT | 删除；L2 发现/静态 peer |
| DTLS 传输 | DTLS-over-L2 或 PSK |
| SDP 连接行 | SDP L2 profile |
| QoS/ECN | PCP/WMM；AP 上行遥测 |
| OAM | LLDP/CFM；计数器 |
| 浏览器互通 | 网关（本阶段不做） |

### Phase 6：优化

- pacing / GCC；
- NACK/RTX/FEC 参数；
- AP 上行 airtime 反馈；
- WMM/EDCA；
- 最后再做“on MAC”。

---

## 3. 功能分类：哪些必须保留、哪些可裁

### 3.1 必须保留（本场景）

| 功能 | 原因 |
|---|---|
| H.264 RTP 打包（RFC 6184） | 视频基础 |
| Opus RTP（RFC 7587） | 音频基础 |
| RTP 序号/时间戳/SSRC | 抖动缓冲、同步、丢包检测 |
| RTCP SR/RR | A/V sync、接收质量 |
| NACK/PLI/RTX | 丢包恢复、关键帧恢复 |
| SRTP | 局域网也需要加密/完整性 |
| 抖动缓冲 | 吸收 Wi-Fi 抖动 |
| 音视频同步 | 你的明确需求 |
| pacing | 避免突发打爆 AP 队列 |
| 最小 SDP | 编解码/参数协商 |

### 3.2 可以裁剪（本场景）

| 功能 | 原因 |
|---|---|
| ICE/STUN/TURN | 局域网、AP 已知 STA |
| DataChannel/SCTP | 当前只有音视频 |
| simulcast/SVC | 单流、单接收端 |
| 多方/SFU | 单 STA 到 AP |
| 浏览器 API | AP 是自定义接收端 |
| TURN | 无 NAT 穿透 |
| 视频会议 AEC/AGC | 文件源，不需要 |
| 复杂 SDP/ICE 属性 | 用最小 profile |

### 3.3 受影响、需要补丁

| 功能 | 影响 |
|---|---|
| 流复用 | 没有端口，需要 flow_id |
| MTU/分片 | 没有 IP 分片，需要应用层处理 |
| 校验/完整性 | 没有 UDP checksum，需要 SRTP/HMAC |
| DTLS 传输 | 没有 UDP，需要 DTLS-over-L2/PSK |
| SDP 候选 | 没有 IP/端口，需要 L2 profile |
| QoS/ECN | 没有 DSCP/ECN，需要 PCP/WMM/遥测 |
| 发现/会话 | 没有 DHCP/DNS，需要 L2 发现 |
| OAM | 没有 ICMP，需要 LLDP/CFM |

---

## 4. 六条 1080p 素材怎么用

现有素材是 5–7 Mbps 成品，**不能直接当 10/15/20 Mbps 用**。需要先重编码。

### 4.1 预处理

- 视频：H.264 High、yuv420p、固定 GOP、`sc_threshold=0`、先关闭 B 帧；
- 目标码率：10 / 15 / 20 Mbps CBR；
- 音频：AAC → Opus 48 kHz；5.1 下混为立体声；
- 时间戳：24/25/30 fps 对应 90 kHz 步长 3750/3600/3000，整数，适合验证 RTP；
- 每条输出记录：文件名、fps、目标码率、实际码率、GOP、音频 layout、SHA256。

### 4.2 建议测试矩阵

| 阶段 | 素材 | 配置 | 目的 |
|---|---|---|---|
| Smoke | `1080p30_1_artemis_origins_85s` | 10 Mbps，视频-only | 先通 RTP/L2/解码 |
| Audio | 同上 | 15 Mbps + Opus | A/V sync |
| FPS | 24/25/30 各一条 | 15 Mbps + Opus | 帧率/时间戳 |
| Bitrate | 30 fps 一条 | 10/15/20 Mbps | 空口余量/画质 |
| Content | 六条全部 | 15 Mbps + Opus | 内容/运动复杂度 |
| Loss | 30 fps 一条 | 0.01/0.1/0.5% + 突发 | NACK/FEC/RTX |
| Long run | 30 fps 一条 | 15 Mbps，10 min | 回绕/稳定性 |

不要同时跑 UDP 和 L2：同信道会互相抢空口，比较无效。必须顺序跑。

---

## 5. 关键原则

1. **先有 baseline，再裁剪。**
2. **先有 transport seam，再换 L2。**
3. **不要重写 RTP/RTCP/SRTP。**
4. **不要用自定义 RTC2 作为起点。**
5. **每次只改一个变量。**
6. **所有结论必须有 pcap/指标对照。**
7. **先视频-only，再加音频；先文件，再实时采集。**
8. **先 1080p30/10 Mbps，再 15/20 Mbps。**

---

## 6. 一句话建议

**思路 1 是对的，但要把它从“实现完整 WebRTC”缩小成“实现最小 RTP/RTCP/SRTP 媒体面 + 可切换传输”；思路 2 只能作为最终形态，不能作为起点。**
