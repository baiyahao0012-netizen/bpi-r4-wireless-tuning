# GStreamer 媒体层网络功能测试

日期：2026-11-09  
设备：Raspberry Pi 5（RPI-5），GStreamer 1.26.2  
路径：Pi `wlan1`（192.168.240.126）→ BPI-R4 AP → Pi `eth0`/macvlan（192.168.240.154，netns `rtcns`）

> **重要限定：接收端是同一台 Pi 的 netns/macvlan，不是 AP 接收端。**
> 这组结果只能证明“媒体层 + 真实 Wi-Fi/AP bridge 链路”可用，**不能作为 STA→AP 基线**。
> STA→AP 基线必须在 AP 上终止 RTP（AP `udpsrc`/解码或落盘），或由 AP 后面的有线参考接收端明确标注为 reference，不能把同机接收冒充 AP 接收。

## 1. 视频 RTP

- 素材：`1080p30_1_artemis_origins_85s.mp4`（1080p30）
- 发送：10 s，H.264 RTP → UDP → `wlan1`，源 `192.168.240.126`
- 接收：`udpsrc` → `rtpjitterbuffer` → `rtph264depay` → `avdec_h264` → 160×90 I420 → `filesink`
- 结果：
  - sender rc=124（`timeout` 主动结束，预期）
  - receiver rc=0
  - 输出 YUV：6,480,000 bytes
  - 160×90 I420 每帧 21,600 bytes → **300 帧**
  - 10 s × 30 fps → **帧数正好 300**
- 判定：**PASS**（真实 Wi-Fi/AP/Ethernet 路径、RTP、jitter buffer、H.264 解码均正常）

## 2. 音频 RTP

- 发送：10 s，AAC 解码 → Opus 编码 → RTP → UDP → `wlan1`
- 接收：`udpsrc` → `rtpjitterbuffer` → `rtpopusdepay` → `opusdec` → WAV
- 结果：
  - sender rc=124（`timeout` 主动结束，预期）
  - receiver rc=0
  - 输出 WAV：1,866,284 bytes
  - WAV 头在 timeout 终止时未完全回填，`wave` 读出的总帧数不可信；音频数据已实际写入
- 判定：**PASS（功能）**；WAV 头/精确时长需要后续用 EOS 正常收尾再测

## 3. AP 侧抓包（STA→AP 路径验证，不是基线）

在 AP `phy0.1-ap0` 抓 `udp port 5004`：

```text
2000 packets captured
src 192.168.240.126:35758 -> dst 192.168.240.1:5004
single SSRC
```

说明：

- STA 的 RTP 确实到达 AP；
- 但 `phy0.1-ap0` 抓包看到的是 **A-MSDU 聚合帧**，一个抓包记录里可能包含多个 RTP 包，序列号会呈现跳变；
- 因此这份 pcap **不能直接算丢包率/帧完整率**，只能证明路径方向；
- AP 侧 GStreamer 接收端尚未跑通（`gst-launch` 已装，pipeline 还没写出可解码文件）。

## 4. 本地功能测试（前一轮）

见 `GST_LOCAL_TEST_20261109.md`：

- H.264 解码：rc=0，85 s 素材 12 s 解完
- H.264 RTP 打包：rc=0
- AAC→Opus RTP：rc=0
- 视频 RTP probe：5933 包，seq gap=0
- 音频 RTP probe：344 包，seq gap=0
- PASS=5，FAIL=0

## 5. 路由隐患核查（2026-11-09 晚）

### 隐患 A：确认存在

修复前：

```text
ip route get 192.168.240.1 from 192.168.240.126
→ dev eth0
```

10 s 发送测试：

| 计数器 | 增量 |
|---|---:|
| Pi `wlan1` TX bytes | **0** |
| Pi `eth0` TX bytes | **+7,467,563** |
| AP station `rx bytes` | **+24**（管理帧量级） |

结论：`udpsink bind-address=.126` 只改源 IP，**没有改出口**；媒体实际走了有线。此前任何“无线”结论都不能用。

### 修复

增加源地址策略路由：

```bash
sudo ip rule add from 192.168.240.126 lookup 100
sudo ip route replace 192.168.240.0/24 dev wlan1 src 192.168.240.126 table 100
```

修复后：

| 计数器 | 增量 |
|---|---:|
| Pi `wlan1` TX bytes | **+7,463,596** |
| Pi `eth0` TX bytes | **+4,553**（SSH/控制） |
| AP station `rx bytes` | **+7,463,620** |

三者对上，证明媒体确实走了 `wlan1 → AP`。

`send_ap.sh` 已加路由守卫：若 `ip route get ... from .126` 不是 `dev wlan1`，直接拒绝发送。

### 隐患 B：确认存在，已处理

旧脚本 `net_test.sh` / `net_audio_test.sh` 仍引用已删除的 `rtcns` 和 `.154`。已改名为：

```text
net_test_DEPRECATED.sh
net_audio_test_DEPRECATED.sh
```

并删除 `run_net.sh` / `run_audio.sh` 符号链接，避免误跑。

## 6. 尚未验证

- 10/15/20 Mbps 码率矩阵
- SRTP 加解密
- RTCP SR / A-V sync
- 丢包 / NACK / PLI / RTX / FEC
- AP 自己作为 RTC 接收端（AP 已装 `gst-launch` 和部分 RTP 插件，但接收 pipeline 尚未跑通）
- 多 STA / 长时运行

## 7. 复现

```bash
# 先确保媒体路由走 wlan1
sudo bash /home/bai/rtc_test/setup_media_route.sh

# STA -> AP 发送（脚本内有路由守卫）
cd /home/bai/rtc_test
./send_ap.sh 10
```

同机 netns 接收脚本已废弃，不要再用。

当前共享终端：`tmux attach -t rtc`。

## 7. 2026-11-09 复核补充（只读核查）

- Pi 上 netns `rtcns` / macvlan / `.154` 已确认删净：`ip netns list` 为空，无 macvlan 接口。
- **路由隐患（待修）**：`eth0=.153` 与 `wlan1=.126` 同在 `192.168.240.0/24`，eth0 metric 100 优先、wlan1 metric 600；`ip route get 192.168.240.1 from 192.168.240.126` 返回 **`dev eth0`**。`udpsink` 的 `bind-address` 只改源 IP、不改出口网卡，媒体可能从有线 eth0 溜出。下一轮必须按"先记计数器基线 → 跑 10 s → 看增量"归因，并以 AP `station dump` rx bytes 增量对齐 wlan1 TX 增量作为走无线的硬证据。
- AP 当前接收进程：`gst-launch-1.0 udpsrc port=5004 ! fakesink`（PID 21365），只听不存；`/tmp/rx.log`、`/tmp/rx2.log` 均 0 字节，无落盘文件。
- AP GStreamer 1.24.8 已有插件：`udpsrc` `rtpjitterbuffer` `rtph264depay` `rtpopusdepay` `filesink`；**缺** `h264parse`、`avdec_h264`。AP 端只能 depay 后落原始 H.264 文件，解码拿回 Pi/PC 做。
- AP station dump：STA `90:de:80:1c:6a:7a`，signal -48 dBm，tx retries 4374；计数器为开机累计值，不能按轮归因。
- 旧脚本 `net_test.sh` 仍引用已删除的 netns/`.154`，**禁止再跑**；`send_ap.sh` 发送目标为 AP `.1:5004`，但出口路由存疑（见上）。
