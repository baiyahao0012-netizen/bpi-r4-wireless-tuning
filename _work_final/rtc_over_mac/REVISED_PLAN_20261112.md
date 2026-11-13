# RTC over MAC 修订计划（视频承载，先基线后 L2）

日期：2026-11-12  
适用范围：继续 RTC over MAC 研究；**传输载荷仍用视频**；先做媒体层 + UDP baseline，再做 L2 对比。  
本文件修正 `NEXT_PLAN_LAPTOP_RX_20261111.md` 和 `L1_LAPTOP_SMOKE_20261111.md` 中的表述。

---

## 0. 结论

- 研究方向不变：私有网络、STA 无线上行、AP 仅 bridge、笔记本算力平台接收/处理；
- 当前用视频作为传输载荷是合理的：它提供稳定、可重复、可测的码率/帧/时延，适合做**传输层基线**；
- GenAI 的 Token/任务级指标是后续另一层验证，不与当前视频传输基线混在一起；
- 当前 `L1` 只是 Python 探针的 clean-path 冒烟，不是正式 baseline；
- 正式 baseline 必须换 GStreamer 接收端，并补齐时钟、完整视频素材和指标。

---

## 1. 对五点评审的处理

### 1.1 跨机时钟同步：接受，加入门禁

**现状：**

- Pi：`timedatectl` 显示 system clock synchronized: yes，NTP active；
- Windows：`w32time` 服务 **Stopped / Manual**，`w32tm /query /status` 报 0x80070426；
- 因此当前 PC/Pi 的时钟偏移**没有可引用的实测值**，不能直接用于 RTCP SR/A-V skew 对账。

**修订：**

- 每次涉及 RTCP SR / A-V sync 的测试，测试前后各记录一次：
  - Pi：`timedatectl`、`chronyc tracking`（若可用）、`date +%s.%N`；
  - PC：启动/确认 `w32time`，`w32tm /resync`、`w32tm /query /status`，或对同一 NTP 源测量 offset；
- 记录 PC 与 Pi 相对同一 NTP 源的 offset，取差值作为跨机偏移；
- RTCP 对账时把该偏移写入误差项；超过门限（建议 5 ms）先修正时钟，不继续 A/V 结论；
- 视频-only baseline 不依赖跨机时钟，可先跑；**A/V sync 必须过时钟门禁**。

### 1.2 策略路由：改写为“重启后会丢失，跑前复核”

**现状（已实测）：**

```text
ip rule: 32765: from 192.168.240.126 lookup 100
table 100: 192.168.240.0/24 dev wlan1 src 192.168.240.126
ip route get 192.168.240.2 from 192.168.240.126
  → dev wlan1 table 100
```

所以当前**在位**，不是“已丢失”。正确表述：

> 策略路由是运行时配置，Pi 重启后会丢失；每次发送前用 `ip route get ... from .126` 复核出口必须为 `wlan1`，并核对 `wlan1`/AP station 计数器增量。

`send_pc.sh` / `send_ap.sh` 已带路由守卫；`setup_media_route.sh` 用于重开机后恢复。

### 1.3 探针能力边界：接受，明确标注

`pc_rtp_receiver.py` 只适用于 **clean-path 冒烟**：

- 不处理乱序：序号差值不是 0/1 就计为 gap，T6 类乱序场景不能拿它判读；
- 无 jitterbuffer、无 RTCP 收发、不能解 SRTP；
- 固定超时窗口收包，尾部 B 帧/末帧滞留会造成 301/302 一类偏差；
- 只能证明“RTP 到达 + H.264 可解码”，不能证明正式媒体层功能。

正式基线必须换 GStreamer 接收端（`udpsrc → rtpjitterbuffer → rtph264depay → h264parse → avdec_h264`），再补 RTCP/SRTP/音频。

### 1.4 Windows GStreamer：难点在 SRTP 密钥回调，不是操作系统本身

区分两件事：

| 目标 | 可行性 | 关键点 |
|---|---|---|
| Windows 原生 GStreamer 收 RTP/H.264 | 可行 | 装 runtime，`gst-launch` 即可 |
| Windows 原生 SRTP 接收 | 可行但有门槛 | `srtpdec` 无 `key` 属性，必须实现 `request-key` 回调；`gst-launch` 配不了 |
| Python/PyGObject 绑定 | 风险高 | Windows 上 `gi`/gst-python 安装麻烦，不应作为第一选择 |
| Linux VM 桥接以太网 | 最稳 | GStreamer + PyGI + SRTP + 后续 l2src 都可做 |

修订选型：

1. **clean UDP baseline**：Windows 原生 GStreamer runtime + `gst-launch`；
2. **SRTP**：Linux VM（PyGI）或小型 C/C++ GStreamer 应用，不依赖 Windows Python gi；
3. **L2**：Linux VM 的 AF_PACKET `l2src` 最顺；Windows 需 Npcap，后置。

### 1.5 码率：本轮不派生 10/15/20 Mbps

按最新决定：

- **直接使用用户提供的六条 1080p 原始视频**，不重编码、不派生 10/15/20 Mbps；
- 六条素材的源码率约 2.1–7.2 Mbps，覆盖 24/25/30 fps，足够做本轮传输 baseline；
- 每条素材先记录 `ffprobe` 的时长、帧数、分辨率、fps、视频/音频码率；
- 每条素材**跑完整时长**，不用 10 s 截断；
- 音频：源 AAC 需解码后转 Opus 48 kHz；25 fps 的 5.1 素材先下混立体声；
- 若后续需要 10/15/20 Mbps 码率矩阵，另立阶段，不在本轮混入。

> Pi 5 没有确认可用的 H.264 硬件编码器；本轮不把实时编码 CPU 混入传输结论。

六条素材（Pi 路径：`/home/bai/rtc_test/testset_1080p/`）：

| 文件 | fps | 时长 | 视频码率 | 音频 | 用途 |
|---|---:|---:|---:|---|---|
| `1080p24_1_sintel_trailer_52s.mp4` | 24 | 52.21 s | 2108 kb/s | AAC 立体声 | 24fps 冒烟/备用 |
| `1080p24_2_caminandes_90s.mp4` | 24 | 90.04 s | 6999 kb/s | AAC 立体声 | 24fps 内容 |
| `1080p25_3_bbb_trailer_33s.mp4` | 25 | 32.99 s | 7162 kb/s | AAC 5.1 | 25fps，需下混 |
| `1080p30_1_artemis_origins_85s.mp4` | 30 | 85.33 s | 4999 kb/s | AAC 立体声 | 30fps smoke |
| `1080p30_2_artemis_avatar_76s.mp4` | 30 | 75.77 s | 4997 kb/s | AAC 立体声 | 30fps 内容 |
| `1080p30_3_artemis_recap_90s.mp4` | 30 | 90.07 s | 5021 kb/s | AAC 立体声 | 30fps 内容 |

本轮全部**跑完整时长**；不做 10/15/20 Mbps 派生。

---

## 2. 三个形态要先分清

```text
A. UDP baseline（现在）
   RTP/RTCP/SRTP → UDP/IP → Wi-Fi MAC

B. RTC over MAC（本轮目标）
   RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC
   去掉 UDP/IP，但 RTC 层仍在

C. MAC-native（研究最终形态，后续）
   视频帧/Token → MAC 调度器
   RTC 层消失，deadline/重要性/重传由 MAC 统一处理
```

本轮验收只到 **B**；不要把 B 说成“RTC 层消失”。  
如果研究目标包含 C，需要另立阶段，不能只靠 `l2sink/l2src` 完成。

## 2.1 修订后的测试顺序

```text
P0  L0 收口（Pi 本地）
    T3/T4 显式 EOS → 302/302
    T7 NACK/PLI/RTX 闭环
    T8 音频 jb/rtpbin 双流
        │
P1  笔记本接收端
    Windows GStreamer（clean UDP）
    或 Linux VM（完整）
    时钟检查、防火墙、绑定 .2
        │
P2  L1 UDP 视频-only baseline
    六条 1080p 原始视频逐条跑完整时长
    路由守卫 + 计数器 + AP 抓包 + 帧数/时延/抖动
        │
P3  L1 音频 + RTCP SR + A/V sync + SRTP
    时钟偏移门禁
        │
P4  冻结 UDP baseline
        │
P5  L2 l2sink/l2src
    同一视频、同一接收端、同一指标
        │
P6  L2 差分 + 补丁 + 长稳
```

> 当前 Python 探针只用于 P2 之前的连通性冒烟；不进入正式 baseline 表。

---

## 3. 每阶段验收

### P0

- T3/T4：302/302，0 解码错误；
- T7：探针看到 205/206 出站，RTX 有回填，丢包恢复优于关闭；
- T8：音频 jb/rtpbin 双流下 A/V p95 ≤ 40 ms（本地基准）。

### P1

- 笔记本绑定 `192.168.240.2`；
- GStreamer 能收 5004/5006；
- 防火墙放行；
- 时钟偏移有记录；
- 本地 UDP 回环先通。

### P2

- `ip route get .2 from .126 → dev wlan1`；
- `wlan1` TX 增量 ≈ 码率 × 时长；
- `eth0` TX 增量仅控制流量；
- AP station rx 增量对得上；
- AP `phy0.1-ap0` 抓到 RTP；
- 源帧数 = 解码帧数；
- 记录时延、抖动、帧完整率、CPU、AP airtime/retries。

### P3

- Opus PT=111、独立 SSRC；
- RTCP SR 的 NTP↔RTP 映射自洽；
- 跨机时钟偏移在门限内；
- SRTP 解密 0 drop；
- A/V skew 有 p50/p95。

### P5/P6

- L2 pcap 无 IP/UDP 头；
- 目的 MAC = 笔记本以太网 MAC；
- 与 UDP baseline 同条件对比；
- 未受影响功能回归，受影响功能有补丁记录。

---

## 4. 当前立即可做

1. 六条原始视频已复制到 Pi：`/home/bai/rtc_test/testset_1080p/`；
2. 对六条素材逐条 `ffprobe`，记录时长、帧数、fps、视频/音频码率；
3. 在 PC 上装 GStreamer runtime（clean UDP）或准备 Linux VM（完整）；
4. 修正 `w32time`/记录 PC-Pi 时钟偏移；
5. 用 `1080p30_1` 全片先跑一次 GStreamer UDP 接收，确认源帧数 = 解码帧数；
6. 再按六条素材逐条跑完整视频，最后补音频/RTCP/SRTP/A-V sync。

---

## 5. 一句话

继续用视频做 RTC over MAC 的传输载荷是对的；当前要修的是**基线方法学**，不是研究方向：补时钟门禁、换正式 GStreamer 接收端、明确探针边界、用六条原始视频跑完整时长，然后冻结 UDP baseline、进入 B 形态（RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC）。
