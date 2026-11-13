# L1 UDP 六片完整视频基线（冻结 v1）

日期：2026-11-12  
拓扑：

```text
Pi 5 wlan1 192.168.240.126
  → BPI-R4 AP（仅 bridge）
  → 笔记本以太网 192.168.240.2
```

## 1. 测试配置

- 接收端：Windows GStreamer 1.26.11；
- 六条用户提供的 1080p 原始视频，**不重编码、不派生 10/15/20 Mbps**；
- 每条跑完整时长；
- 视频-only；
- 接收管线：

```text
udpsrc address=192.168.240.2 port=5004
  buffer-size=8388608 timeout=30s
  ! rtpjitterbuffer latency=200
  ! rtph264depay ! h264parse ! avdec_h264
  ! videoconvert ! videoscale
  ! video/x-raw,format=I420,width=320,height=180
  ! filesink sync=false
```

- 发送端：`send_testset_full.sh`，路由守卫 `dev wlan1 table 100`；
- 接收端预热：10 s（早期 5 s 会丢启动窗口，已修正）。

## 2. 六片实测

| 素材 | fps | 时长 | 源码率 | 源帧 | 解码帧 | 完整率 |
|---|---:|---:|---:|---:|---:|---:|
| `1080p24_1_sintel_trailer_52s.mp4` | 24 | 52.21 s | 2.11 Mbps | 1253 | 1251 | **99.840%** |
| `1080p24_2_caminandes_90s.mp4` | 24 | 90.04 s | 7.00 Mbps | 2161 | 2160 | **99.954%** |
| `1080p25_3_bbb_trailer_33s.mp4` | 25 | 32.48 s | 7.16 Mbps | 812 | 811 | **99.877%** |
| `1080p30_1_artemis_origins_85s.mp4` | 30 | 85.33 s | 5.00 Mbps | 2560 | 2558 | **99.922%** |
| `1080p30_2_artemis_avatar_76s.mp4` | 30 | 75.77 s | 5.00 Mbps | 2273 | 2271 | **99.912%** |
| `1080p30_3_artemis_recap_90s.mp4` | 30 | 90.07 s | 5.02 Mbps | 2702 | 2700 | **99.926%** |
| **合计** | — | — | — | **11761** | **11751** | **99.915%** |

- 每片发送端 `rc=0`；
- 无 GStreamer 致命错误；
- 每片差 1–2 帧，集中在尾部，属于无 EOS 的末帧/B 帧滞留；
- 没有出现早期 24fps 的 7–13% 丢帧；根因是接收端预热不足，不是 jitterbuffer 算法缺陷。

## 3. 辅助网络指标

早前同一路径 10 s Python RTP 探针：

```text
5933 packets
seq_gaps=0
duplicates=0
jitter≈6.657 ms
```

24fps 全片 RTP 探针：

```text
10673 packets
seq_gaps=0
duplicates=0
unique_timestamps=1253
```

用于证明网络层没有明显丢包；正式时延/CPU/AP airtime 指标尚未系统采集。

## 4. 冻结判定

```text
Baseline: L1 UDP video-only, six full clips
Receiver: Windows GStreamer 1.26.11
Frozen:   v1
Frames:   11751 / 11761 = 99.915%
Tail gap: 1–2 frames per clip
Strict:   NOT YET (11761/11761 pending explicit EOS)
```

**结论：六片 UDP 传输基线 v1 可冻结，作为 L2 对比参照。**  
严格帧级相等仍留作 EOS 复核，不作为进入 L2 的阻塞项。

数据文件：`fullset_baseline.csv`
