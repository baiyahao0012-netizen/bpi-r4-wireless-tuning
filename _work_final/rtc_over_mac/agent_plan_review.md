## 先回答核心问题

**没有偏离，继续做 RTC over MAC，继续用视频作为传输载荷。**

原因：

- 视频是稳定、可重复、可量化的传输载荷，适合先把 **RTP/RTCP/SRTP + UDP/IP vs L2** 的差异测清楚；
- GenAI 的 Token、TTFT、任务正确性是下一层验证，不应现在混进来，否则变量太多；
- 你现在做的是“传输层减法”的 baseline，之后才进入 MAC-aware 和 GenAI 业务层。

但要注意：**当前只是传输 baseline，不是完整 GenAI 研究**。视频能过 L2，不等于 GenAI 业务正确、及时。

---

## 一、先汇报这次检测到的事实

### 1. 策略路由：当前在位，不是“已丢失”

实测：

```text
ip rule:
32765: from 192.168.240.126 lookup 100

table 100:
192.168.240.0/24 dev wlan1 src 192.168.240.126

ip route get 192.168.240.2 from 192.168.240.126
→ dev wlan1 table 100
```

正确表述应为：

> **策略路由是运行时配置，Pi 重启后会丢失；每次发送前用 `ip route get` 复核出口必须为 `wlan1`。**

不是“现在已经丢了”。

### 2. 时钟：Pi 同步正常，PC 的 w32time 没开

- Pi：`timedatectl` 显示 `System clock synchronized: yes`，NTP active；
- Windows：`w32time` 为 **Stopped / Manual**，`w32tm /query /status` 报 0x80070426；
- 所以当前 **PC/Pi 跨机偏移没有可引用的实测值**。

这会影响：

- RTCP SR 的 NTP↔RTP 对账；
- A/V skew；
- 任何跨机时间结论。

### 3. 笔记本接收栈：只有 Python/PyAV 探针

- 没有 GStreamer；
- `pc_rtp_receiver.py` 能收 RTP、重组 H.264、PyAV 解码；
- 但它**不处理乱序、无 jitterbuffer、无 RTCP、不能解 SRTP、固定窗口收包**；
- 只能做 clean-path 冒烟，不能做正式 baseline。

### 4. 当前 L1 冒烟结果

真实路径：

```text
Pi wlan1 .126 → AP bridge → 笔记本以太网 .2
```

10 s 视频-only：

| 指标 | 实测 |
|---|---:|
| RTP 包 | 5933 |
| seq gaps | 0 |
| 时间戳 | 302 |
| 解码帧 | 301/302 |
| 线上速率 | 5.97 Mbps |
| 到达抖动 | 6.657 ms |
| Pi wlan1 TX 增量 | 7,463,296 B |
| AP station rx 增量 | 7,463,296 B |
| Pi eth0 TX 增量 | 8,548 B（控制） |

**结论：路径和基本 RTP/H.264 功能通过，但不是正式媒体层基线。**

### 5. Pi 编码能力

- 有 `libx264`；
- 有 `h264_v4l2m2m` wrapper，但 `v4l2-ctl` 只看到 ISP，**没有确认可用的 H.264 硬件编码器**；
- 所以不能假设 Pi 能实时硬编 1080p30 20 Mbps。

---

## 二、对你五点评审的处理

### 1. 跨机时钟同步：接受，加入门禁

新增测试前后检查：

```text
PC：
  Start-Service w32time
  w32tm /resync
  w32tm /query /status

Pi：
  timedatectl
  chronyc tracking（若可用）
  date +%s.%N
```

要求：

- 测前、测后各记录一次；
- 对同一 NTP 源比较 PC/Pi offset；
- 超过 5 ms 先修正，不继续 A/V 结论；
- RTCP 对账把偏移写进误差项。

视频-only baseline 可以先跑；**A/V sync 必须过时钟门禁**。

### 2. 策略路由：改写为“重启后会丢失”

已修正文档：

- 当前在位；
- 每次发送前 `ip route get` 复核；
- 重启后执行 `setup_media_route.sh`；
- 计数器仍要核对 `wlan1` TX / `eth0` TX / AP station rx。

### 3. 探针能力边界：接受，明确标注

`pc_rtp_receiver.py` 只能做：

> **clean-path 连通性 + RTP/H.264 冒烟。**

不能用于：

- T6 乱序判读（会把乱序算成 gap）；
- 正式帧完整率；
- RTCP/SRTP/A-V sync；
- 反馈/重传测试。

正式 baseline 必须换 GStreamer 接收端。

### 4. Windows GStreamer：难点是 SRTP 回调，不是“Windows 不行”

要分清：

| 目标 | 路线 |
|---|---|
| Windows 收 RTP/H.264 | 原生 GStreamer runtime + `gst-launch`，可行 |
| Windows 解 SRTP | `srtpdec` 需要 `request-key` 回调；`gst-launch` 做不到 |
| Python/PyGObject | Windows 上 `gi` 绑定安装麻烦，不作为首选 |
| 完整 SRTP/L2 | Linux VM 桥接以太网最稳；或写小型 C/C++ GStreamer 应用 |

所以：

- **clean UDP baseline** 可以先上 Windows 原生 GStreamer；
- **SRTP** 不要卡在 Windows Python gi 上，直接用 Linux VM 或 C 应用。

### 5. 码率阶梯：接受，先定方法

正式传输 baseline 的 10/15/20 Mbps 素材：

- **在 PC 上离线生成**，不占 Pi 实时 CPU；
- 1920×1080，30 fps，H.264；
- `-bf 0`，GOP=30，`yuv420p`；
- CBR：

```bash
ffmpeg -i source.mp4 -t 10 -an \
  -c:v libx264 -preset veryfast \
  -b:v 10M -maxrate 10M -bufsize 20M \
  -x264-params nal-hrd=cbr:force-cfr=1 \
  -g 30 -bf 0 -pix_fmt yuv420p \
  out_10m.mp4
```

- 10 / 15 / 20 Mbps 各生成 10 s 和 30 s；
- `ffprobe` 核对码率/帧率/GOP/帧数；
- SHA256 入 manifest；
- Pi 只负责发送/解码，不把 x264 编码 CPU 混入传输结论；
- 若要做实时摄像头编码，另开一组测 Pi x264 的 fps/CPU，达不到 30 fps 就降帧率/分辨率，不与传输 baseline 混用。

---

## 三、修订后的执行顺序

```text
P0  L0 收口
    T3/T4 显式 EOS → 302/302
    T7 NACK/PLI/RTX 闭环
    T8 音频 jb/rtpbin 双流

P1  笔记本接收端
    Windows 原生 GStreamer（clean UDP）
    或 Linux VM（完整）
    时钟检查、防火墙、绑定 .2

P2  L1 UDP 视频-only baseline
    10 Mbps 起步 → 15/20 Mbps
    路由守卫 + 计数器 + AP 抓包 + 帧数/时延/抖动

P3  L1 音频 + RTCP SR + A/V sync + SRTP
    跨机时钟门禁

P4  冻结 UDP baseline

P5  L2 l2sink/l2src
    同一视频、同一接收端、同一指标

P6  L2 差分 + 补丁 + 长稳
```

当前 Python 探针只用于 P2 之前的连通性冒烟，不进入正式 baseline 表。

---

## 四、现在最该做的三件事

1. **PC 装 GStreamer runtime**，先用 `gst-launch` 收 RTP/H.264；SRTP 后续用 Linux VM 或 C 应用。
2. **修时钟**：启动 `w32time`，记录 PC/Pi 对同一 NTP 源的偏移。
3. **在 PC 生成 10 Mbps CBR 10 s 素材**，用 GStreamer 收同一流，确认 **302/302**，再跑 15/20 Mbps。

修订后的完整方案：[REVISED_PLAN_20261112.md](_work_final/rtc_over_mac/REVISED_PLAN_20261112.md)  
这次 L1 冒烟记录（已补探针边界）：[L1_LAPTOP_SMOKE_20261111.md](_work_final/rtc_over_mac/L1_LAPTOP_SMOKE_20261111.md)

**一句话：方向不变，继续视频 + RTC over MAC；现在先把接收端、时钟、码率阶梯这三件基线方法学补齐，再冻结 UDP baseline，然后进 L2。**