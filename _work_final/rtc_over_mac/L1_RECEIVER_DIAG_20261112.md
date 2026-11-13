# L1 接收端诊断：GStreamer、jitterbuffer 与全片对账

日期：2026-11-12  
拓扑：Pi wlan1 `.126` → AP bridge → 笔记本以太网 `.2`

## 1. 已确认可用

- Windows GStreamer 1.26.11 已解包到 `C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64`；
- `udpsrc → rtph264depay → h264parse → avdec_h264 → videoconvert → videoscale → filesink` 可接收真实 RTP；
- 30 fps 10 s 测试：**300/300 帧**；
- 30 fps 85.33 s 测试：**2556/2560 帧**（带 jitterbuffer，99.84%）；
- Python RTP 探针（24fps 全片）：**10673 包，0 seq gap，0 duplicate，1253 个时间戳**，网络层无丢包；
- 路由守卫：`dev wlan1 table 100` 通过。

## 2. 发现的问题

### 2.1 早期 24fps 丢帧：根因是接收端未预热

早期 24fps `1080p24_1` 的异常结果：

| 接收配置 | 解码帧 | 源帧 | 完整率 |
|---|---:|---:|---:|
| jb latency=100 | 1094 | 1253 | 87.3% |
| jb latency=100（重复） | 1164 | 1253 | 92.9% |
| jb latency=500 | 1143 | 1253 | 91.2% |
| **无 jb** | **1251** | 1253 | **99.8%** |

Python RTP 探针同一片源：

```text
packets=10673, seq_gaps=0, duplicates=0, unique_timestamps=1253
```

后续修正：

- 把接收端预热时间从 **5 s 提高到 10 s**，并恢复 `rtpjitterbuffer latency=200`；
- 24fps 全片复测：**1251/1253（99.84%）**；
- 六片全量复测：**11751/11761（99.915%）**，详见 `L1_BASELINE_SIX_20261112.md`。

结论修正：

- 网络层没有丢包；
- 早期丢帧主要是**接收端启动/预热窗口**，不是 jitterbuffer 的算法缺陷；
- 当前 jb 配置在充分预热后可用；
- 仍每片差 1–2 帧，属尾部/末帧滞留，需显式 EOS 才能严格相等。

### 2.2 当前六片结果

| 素材 | 源帧 | 解码 | 完整率 |
|---|---:|---:|---:|
| 1080p24_1 | 1253 | 1251 | 99.840% |
| 1080p24_2 | 2161 | 2160 | 99.954% |
| 1080p25_3 | 812 | 811 | 99.877% |
| 1080p30_1 | 2560 | 2558 | 99.922% |
| 1080p30_2 | 2273 | 2271 | 99.912% |
| 1080p30_3 | 2702 | 2700 | 99.926% |
| **合计** | **11761** | **11751** | **99.915%** |

## 3. 当前基线状态

- 六片全量已完成，**L1 UDP video-only transport baseline v1 可冻结**；
- 严格 11761/11761 仍未达到，每片差 1–2 帧，属尾部滞留；
- 该基线用于 L2 同条件对比，正式“严格帧级闭环”需显式 EOS 复核。

## 4. L2 侧进展与阻塞

- Windows 已装 Npcap，Scapy 可用；
- 已写 `l2_probe_send.py` / `l2_probe_recv.py` / `l2_probe_send_win.py`；
- **反向桥接验证通过**：Windows 以太网 → AP → Pi `wlan1`，EtherType `0x88B5` 帧被 AP `phy0.1-ap0` 抓到 5/5，payload `RTC2PROBE` 完整；
- 说明 AP bridge **不会丢弃自定义 EtherType**，L2 路径前提成立；
- Pi → Windows 方向仍需 Pi 侧 `AF_PACKET` 发送；Pi 当前 `sudo` 不接受原密码，无法获得 `CAP_NET_RAW`，所以该方向尚未验证。

## 5. 下一步

1. 恢复 Pi 的 sudo 或给发送程序 `CAP_NET_RAW`，打通 Pi → Windows 的 `0x88B5` 发送；
2. 用显式 EOS/尾部冲刷把 11751/11761 推到严格相等（非 L2 阻塞项）；
3. 以六片 baseline v1 为冻结参照，进入 L2 RTP/RTCP/SRTP 封装；
4. L2 完成后按影响矩阵做差分、补丁、回归。
