# 04 GStreamer 管线逐项注释（开源媒体层）

本项目被测的"媒体层"就是下面这些 **GStreamer 现成元件** 用 `!` 串成的管线。
`gst-launch-1.0` 是命令行启动器；元件（element）之间通过 pad（端口）传递 buffer。

---

## 一、发送端：视频 RTP

```bash
gst-launch-1.0 -q -e \
  filesrc location=1080p30_1_artemis_origins_85s.mp4 \
  ! qtdemux \
  ! h264parse \
  ! rtph264pay config-interval=1 pt=96 \
  ! udpsink host=192.168.240.1 port=5004 bind-address=192.168.240.126 sync=true
```

| 元件 | 干什么 | 注释要点 |
|---|---|---|
| `filesrc` | 读文件字节流 | `location=` 指定素材路径 |
| `qtdemux` | MP4/MOV 解封装，把音频轨、视频轨拆开 | MP4 容器格式叫 QuickTime/ISOBMFF |
| `h264parse` | 规范化 H.264 码流，提取 SPS/PPS 参数集 | 没有它，payloader 拿不到解码器参数 |
| `rtph264pay` | 把 H.264 NAL 切片打包成 RTP（FU-A/STAP-A） | RFC 6184 |
| `config-interval=1` | 每个关键帧（IDR）都带上 SPS/PPS | 接收端中途加入也能立刻解码 |
| `pt=96` | 动态载荷类型 96，标识 H.264 | 接收端 caps 要对上 |
| `udpsink` | 把 RTP 包从 UDP socket 发出去 | 这是 baseline 传输；L2 阶段换成 `l2sink` |
| `host/port` | 目的 IP:端口 | baseline 用 IP/UDP；L2 阶段换成目的 MAC + flow_id |
| `bind-address` | 绑定源 IP | **只改源 IP，不改出口网卡**；出口由路由表决定（见 07 号脚本） |
| `sync=true` | 按时间戳节流发送，模拟实时节奏 | 否则文件会瞬间读完 |
| `-q` | 安静模式，少打日志；`-e` | 收到 EOS 时让管线正常收尾 |

## 二、发送端：音频（AAC → Opus → RTP）

```bash
gst-launch-1.0 -q -e \
  filesrc location=素材.mp4 \
  ! qtdemux \
  ! aacparse ! avdec_aac \
  ! audioconvert ! audioresample \
  ! opusenc ! rtpopuspay pt=111 \
  ! udpsink host=192.168.240.1 port=5006 bind-address=192.168.240.126 sync=true
```

| 元件 | 干什么 |
|---|---|
| `aacparse` | 解析 AAC 帧头 |
| `avdec_aac` | 解码 AAC 成原始 PCM |
| `audioconvert` | 采样格式/声道转换（立体声对齐） |
| `audioresample` | 重采样到 Opus 需要的 48 kHz |
| `opusenc` | PCM 编码成 Opus（RFC 6716，低延迟、内置 FEC/PLC） |
| `rtpopuspay` | Opus 打包成 RTP，一包一帧（RFC 7587） |
| `pt=111` | Opus 的动态载荷类型 |

> 为什么音频要转 Opus：AAC 的 RTP 封装（RFC 3640）参数多、抗丢包弱、端到端延迟高；
> Opus 是 RTC 标准音频编码，封装简单、低延迟、抗丢包，第一阶段就用它。

## 三、接收端：视频（本地回环 / 有线参考接收）

```bash
gst-launch-1.0 -q \
  udpsrc address=192.168.240.154 port=5004 \
  caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! rtpjitterbuffer latency=100 \
  ! rtph264depay ! h264parse ! avdec_h264 \
  ! videoconvert ! videoscale \
  ! video/x-raw,width=160,height=90,format=I420 \
  ! filesink location=/tmp/rx_160x90.yuv
```

| 元件 | 干什么 | 注释要点 |
|---|---|---|
| `udpsrc` | 绑定 UDP 端口收包 | baseline 接收端；L2 阶段换成 `l2src` |
| `caps="application/x-rtp,..."` | 声明 RTP 流的媒体类型/编码/PT/时钟率 | 元件靠 caps 协商；不写可能连不上 |
| `media=video` | 视频轨 | —— |
| `encoding-name=H264` | RTP 负载格式名 | Opus 对应 `OPUS` |
| `payload=96` | 必须和发送端 `pt=96` 一致 | —— |
| `clock-rate=90000` | 视频 RTP 时钟 90 kHz | Opus 是 48000 |
| `rtpjitterbuffer latency=100` | 抖动缓冲：缓存 100 ms，重排乱序包 | 抗空口抖动；latency 越大越稳但延迟越高 |
| `rtph264depay` | RTP 解封装，重组 FU-A/STAP-A 回 NAL | `rtph264pay` 的逆操作 |
| `h264parse` | 规范化 H.264，喂给解码器 | —— |
| `avdec_h264` | 软解 H.264 成原始 YUV（I420） | AP 上没有这个插件，所以 AP 只落盘不解码 |
| `videoconvert` | 颜色格式转换 | —— |
| `videoscale` | 缩放到 160×90 | 测试期缩小画面，减小落盘体积、加快统计 |
| `video/x-raw,...` | 固定输出格式/尺寸/像素格式 | I420 = YUV420 Planar |
| `filesink` | 写文件（YUV 裸帧序列） | 帧数 = 文件大小 ÷ 每帧字节数 |

**160×90 I420 每帧字节数**：
Y 平面 160×90 + U 平面 80×45 + V 平面 80×45 = 14400 + 3600 + 3600 = **21600 字节/帧**。
收到 YUV 6,480,000 B ÷ 21600 = **300 帧** = 10 s × 30 fps，这就是当时"帧数正好对上"的算法。

## 四、接收端：音频

```bash
gst-launch-1.0 -q \
  udpsrc address=192.168.240.154 port=5006 \
  caps="application/x-rtp,media=audio,encoding-name=OPUS,payload=111,clock-rate=48000" \
  ! rtpjitterbuffer latency=100 \
  ! rtpopusdepay ! opusdec ! audioconvert ! audioresample \
  ! audio/x-raw,rate=48000,channels=2 \
  ! wavenc ! filesink location=/tmp/rx_audio.wav
```

| 元件 | 干什么 |
|---|---|
| `rtpopusdepay` | Opus RTP 解封装 |
| `opusdec` | Opus 解码成 PCM |
| `wavenc` | PCM 封成 WAV |

## 五、AP 端目标接收管线（AP 缺解码器，只落原始 H.264）

```bash
gst-launch-1.0 -q \
  udpsrc port=5004 \
  caps="application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000" \
  ! rtpjitterbuffer latency=100 \
  ! rtph264depay \
  ! filesink location=/tmp/rx.h264
```

- **不接** `h264parse` / `avdec_h264`：AP GStreamer 1.24.8 没有这两个插件；
- 落盘的是 depay 后的原始 H.264 码流（NAL 序列），不是 MP4；
- 把 `rx.h264` 取回 Pi/PC，再接 `h264parse → avdec_h264` 解码数帧（或用 03 号脚本从 pcap 直接重建）。

## 六、L2 阶段要替换的位置（baseline → target）

| 端 | Baseline（UDP/IP） | Target（L2） | 其余管线 |
|---|---|---|---|
| 发送 | `udpsink` | `l2sink`（AF_PACKET + shim） | 完全一致 |
| 接收 | `udpsrc` | `l2src`（AF_PACKET + 去 shim + 分流） | 完全一致 |

> 替换原则：**只换传输元件，RTP/RTCP/SRTP/编解码/抖动缓冲/同步配置一字不改。**
> `--transport udp|l2` 一个开关切换，不复制两份媒体代码。
