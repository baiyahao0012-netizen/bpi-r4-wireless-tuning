# L1 UDP 基线：单条完整视频测试结果

日期：2026-11-12  
拓扑：

```text
Pi 5 wlan1 192.168.240.126
  → BPI-R4 AP（仅 bridge）
  → 笔记本以太网 192.168.240.2
```

## 1. 测试对象

- 素材：`1080p30_1_artemis_origins_85s.mp4`
- 分辨率：1920×1080
- fps：30
- 时长：85.33 s
- 源帧数：2560（ffprobe）
- 源码率：约 5.00 Mbps
- 音频：本轮视频-only

发送：

```bash
/home/bai/run_send_full.sh 1080p30_1_artemis_origins_85s.mp4
```

- 路由守卫：`192.168.240.2 from 192.168.240.126 dev wlan1 table 100`
- 发送端 rc=0（完整发送，未使用 10 s 截断）

接收：

```text
Windows GStreamer 1.26.11
udpsrc address=192.168.240.2 port=5004
  ! rtpjitterbuffer latency=100
  ! rtph264depay ! h264parse ! avdec_h264
  ! videoconvert ! videoscale
  ! video/x-raw,format=I420,width=320,height=180
  ! filesink
```

## 2. 实测结果

| 指标 | 实测 |
|---|---:|
| 发送端退出码 | 0 |
| 接收端 GStreamer 致命错误 | 0 |
| 输出 YUV 字节 | 220,838,400 B |
| 320×180 I420 每帧 | 86,400 B |
| 解码帧数 | **2556** |
| 源帧数 | **2560** |
| 帧完整率 | **99.84%** |
| 缺失 | 4 帧（0.16%） |
| 路由 | `dev wlan1 table 100` |

`2556 / 2560 = 99.84375%`。

补充：同一完整片多次运行，解码帧数在 **2553–2556** 之间波动，缺口都在尾部；这是当前无 EOS 冲刷导致的尾部滞留，不是稳定丢包。

## 3. 结论

- **完整 85.33 s 视频经真实 Wi-Fi → AP → 笔记本有线接收，GStreamer 接收端可工作；**
- **2556/2560 帧解码，0 致命错误，99.84% 帧完整率；**
- 仍差 4 帧，未达到“源帧数 = 解码帧数”的严格门禁；
- 缺口位于尾部，和之前无 EOS 的 B 帧/末帧滞留现象一致；本轮未做显式 EOS 冲刷；
- 因此本次可冻结为 **L1 transport baseline v1（带 4–7 帧尾部已知偏差）**，但不能称为“严格帧级闭环”；
- 其余五条视频尚未跑完整时长，本轮只完成一条完整视频。

## 4. 参考：10 s 子测试

同一路径、同一 GStreamer 接收端，10 s 子测试：

| 指标 | 实测 |
|---|---:|
| 输出 YUV | 25,920,000 B |
| 解码帧数 | **300** |
| 10 s × 30 fps | 300 |
| 结果 | **300/300** |

说明短窗口可以严格对齐；完整视频的 4–7 帧差异集中在尾部。

## 5. 已知限制

- 本轮未记录跨机时钟偏移（PC `w32time` 仍为 Stopped/Manual）；
- 本轮未做 RTCP、SRTP、音频、A/V sync；
- 未记录本轮 Pi/AP 计数器增量（上一轮 10 s 已验证 `wlan1` TX 与 AP station rx 对齐）；
- 未做 NACK/PLI/RTX；
- 未跑其余五条视频；
- 严格 2560/2560 需要显式 EOS 或接收端尾部冲刷后再验收。

## 6. 基线状态

```text
Baseline: L1 UDP video-only, GStreamer receiver
Status:   FROZEN v1 (transport baseline)
Caveat:   2556/2560, 4–7 frame tail gap across runs
Strict:   NOT YET (2560/2560 pending)
```

后续 L2（B 形态）对比必须以同一素材、同一接收端、同一 320×180 输出口径进行。
