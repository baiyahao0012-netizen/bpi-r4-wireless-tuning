# L1 冒烟：STA 无线 → AP → 笔记本有线接收

日期：2026-11-11  
拓扑：

```text
Pi 5 wlan1 192.168.240.126
  → BPI-R4 AP（仅 bridge）
  → 笔记本以太网 192.168.240.2
```

## 1. 结论

- 新场景的**数据路径成立**：笔记本确实从 AP 后面的有线口收到 RTP，解析出单一 SSRC、连续序号和完整 H.264 帧序列；
- **AP 只做 bridge**，没有参与媒体层；
- 但当前笔记本只有 **Python/PyAV 临时探针**，没有 GStreamer 接收端，因此只能算 **L1 冒烟**，不是完整媒体层基线；
- 不能据此冻结 UDP baseline，也不能据此进入 L2 对比。

## 2. 发送与接收

发送（Pi）：

```bash
sudo bash /home/bai/rtc_test/setup_media_route.sh
/home/bai/run_send_pc.sh 10
```

- 素材：`1080p30_1_artemis_origins_85s.mp4`
- 发送 10 s，H.264 RTP，PT=96，源 `192.168.240.126`，目的 `192.168.240.2:5004`
- 路由守卫确认：`192.168.240.2 from 192.168.240.126 dev wlan1 table 100`

接收（笔记本）：

```text
python pc_rtp_receiver.py --host 192.168.240.2 --port 5004 --seconds 18
```

- UDP 绑定笔记本以太网 `.2`
- 解析 RTP 固定头
- 重组 H.264 Annex-B（单 NAL / STAP-A / FU-A）
- PyAV 解码
- 统计 seq、SSRC、PT、时间戳、到达抖动

## 3. 实测结果

| 指标 | 实测 |
|---|---:|
| RTP 包数 | 5933 |
| 载荷字节 | 7,142,872 B |
| 线上字节（Pi wlan1 TX 增量） | 7,463,296 B |
| 线上速率（10 s） | 5.97 Mbps |
| 载荷速率 | 5.71 Mbps |
| seq gaps | 0 |
| duplicates | 0 |
| SSRC | 单 SSRC |
| PT | 96 |
| RTP 时间戳数 | 302 |
| 解码帧数 | 301 |
| 解码错误 | 0 |
| 到达抖动（RFC3550 估算） | 6.657 ms |
| Pi eth0 TX 增量 | 8,548 B（SSH/控制） |
| AP station rx 增量 | 7,463,296 B |

计数器对账：

```text
Pi wlan1 TX 增量 = 10,327,700 - 2,864,404 = 7,463,296 B
AP station rx 增量 = 10,356,956 - 2,893,660 = 7,463,296 B
```

两者完全一致，证明媒体确实走 `wlan1 → AP → 笔记本 .2`，没有走 Pi 的有线口。

## 4. 这说明什么

### 已证明

- 笔记本作为接收端可以从 AP 有线侧收到 RTP；
- AP 桥接自定义/普通以太网流量正常；
- RTP 序号连续、单 SSRC、PT 正确；
- H.264 重组与解码可用；
- 5 Mbps 级 1080p30 经 Wi-Fi + AP + 有线到笔记本，10 s 无丢包、无解码错误；
- 接收端绑定 `.2`、Windows 防火墙未阻断 UDP 5004。

### 尚未证明

- GStreamer `rtpjitterbuffer` / `rtpbin` 在笔记本上的行为；
- RTCP SR/RR、NTP↔RTP 映射、A/V 同步；
- SRTP 解密（`srtpdec` 的 `request-key` 回调）；
- NACK / PLI / RTX / FEC；
- 10 / 15 / 20 Mbps 码率矩阵；
- 10 min 长稳、CPU/内存/温度；
- 源帧数 = 解码帧数严格相等（本次 301/302，尾部/启动窗口因素，需专用 EOS 会话）。

## 5. 与旧场景的差别

媒体流本身：

```text
发送端、RTP/RTCP/SRTP、AP bridge 均不变
只把接收端从 AP/Pi 改到笔记本
```

工程实现：

- 接收端操作系统/网卡/防火墙/接收栈全变；
- 笔记本需要 GStreamer 或等价接收器；
- SRTP 需要 `request-key` 应用；
- L2 阶段需要笔记本侧 `l2src`（Npcap 或 Linux VM）；
- Pi 需要把目的地址从 AP `.1` 改为笔记本 `.2`，并保持策略路由。

所以：**媒体路径上只改接收端；工程上不是只改一行接收端。**

## 6. 探针能力边界（重要）

`pc_rtp_receiver.py` 只能做 **clean-path 冒烟**：

- **不处理乱序**：序号差值不是 0/1 就计入 `seq_gaps`，T6 类乱序场景不能用它判读；
- 无 jitterbuffer、无 RTCP 收发、不能解 SRTP；
- 固定超时窗口收包，尾部 B 帧/末帧滞留会造成 301/302 一类偏差；
- 因此它不能替代 GStreamer 正式接收端，也不能用于正式 baseline 的帧完整率结论。

本次测试也没有记录 PC/Pi 跨机时钟偏移；PC 的 `w32time` 当前为 Stopped/Manual，
所以本报告中的抖动只是到达间隔估计，**不能用于 RTCP SR/A-V skew 对账**。

## 7. 下一步

1. 笔记本装 GStreamer（或 Linux VM 桥接以太网），建立正式接收端；
2. 用 GStreamer `udpsrc → rtpjitterbuffer → rtph264depay → h264parse → avdec_h264` 复测同一 10 s；
3. 再补 Opus、RTCP SR、A/V sync、SRTP；
4. 通过后再派生 10/15/20 Mbps，冻结 UDP baseline；
5. 最后做 L2 `l2sink/l2src` 对比。
