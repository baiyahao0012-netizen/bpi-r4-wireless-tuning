# RTC over MAC 学习代码包（带注释版）

日期：2026-11-09
来源：本项目 Pi 上实际跑过的探针、脚本、pcap 解析器，以及仓库里的最小 RTP 演示。
说明：**注释为学习补充，代码逻辑与原始版本一致**；原始未注释版本保留在上级目录 `rtc_over_mac/`，本目录是带讲解的副本。

---

## 一、先分清三类东西（别把脚手架当成媒体层）

| 类别 | 是什么 | 本包里的文件 |
|---|---|---|
| **被测媒体层** | 开源 GStreamer 现成元件串成的管线（RTP/RTCP/解码/抖动缓冲） | `04_gstreamer_pipelines.md` |
| **测试脚手架** | Shell 脚本：起接收端 → 等 2 秒 → 起发送端 → 判 PASS/FAIL | `05_test_gst_local.sh`、`06_send_ap.sh`、`07_setup_media_route.sh`、`08_net_test_video.sh`、`09_net_test_audio.sh` |
| **测量工具** | Python：收包解析 RTP 头 / 从 pcap 重建 H.264 并数帧 | `01_rtp_header_demo.py`、`02_rtp_probe.py`、`03_pcap_rtp_rebuild.py` |

> 关键认知：现在**没有自研 RTP/RTCP/SRTP 代码**，也没有 L2 传输代码。RTP 打包/解包全是 GStreamer 元件做的；Python 只负责"量"，不负责"传"。

---

## 二、RTP 12 字节固定头（RFC 3550，所有代码都围绕它）

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|V=2|P|X|  CC   |M|     PT      |       sequence number         |  字节 0–3
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           timestamp                           |  字节 4–7
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           synchronization source (SSRC) identifier            |  字节 8–11
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| 字段 | 位数 | 含义 | 本项目取值 |
|---|---|---|---|
| V | 2 | 版本号，必须 = 2 | 2 |
| P | 1 | Padding，末尾有填充字节 | 0 |
| X | 1 | 头后是否有扩展头 | 0 |
| CC | 4 | CSRC 个数（混音用） | 0 |
| M | 1 | Marker，帧边界标记（一帧最后一包置 1） | 由 payloader 置位 |
| PT | 7 | 载荷类型：96=H.264，111=Opus | 96 / 111 |
| sequence number | 16 | 序号，每包 +1，到 65535 回绕 | 连续无 gap 是基本要求 |
| timestamp | 32 | 采样时间戳；视频 90 kHz，Opus 48 kHz | 30fps 视频每帧 +3000 |
| SSRC | 32 | 会话/流标识，一个流一个值 | 视频、音频各一个 |

**为什么去 UDP/IP 不影响这 12 字节**：RTP 头里没有 IP、没有端口、没有校验和；它独立于底层传输。把 UDP/IP 换成 L2 帧，RTP 头一字节都不用改。

---

## 三、推荐阅读顺序

1. **`01_rtp_header_demo.py`** —— 不用任何库，手工拼/拆 12 字节 RTP 头，先把头结构看明白。
2. **`02_rtp_probe.py`** —— 真实收 UDP 包，解析上面这些字段，统计包数/序号缺口/SSRC。理解"测量工具"长什么样。
3. **`04_gstreamer_pipelines.md`** —— 看开源媒体层怎么用一行 `gst-launch` 串起来，每个元件干什么。
4. **`03_pcap_rtp_rebuild.py`** —— 最硬核的一份：从抓包文件里把 RTP 包按 RFC 6184 重组回 H.264（单 NAL / STAP-A / FU-A），再数解码帧数。
5. **`05_test_gst_local.sh`** —— 本地功能测试怎么编排、怎么按退出码判 PASS。
6. **`06_send_ap.sh`** —— 发送脚本 + 路由护栏（防止媒体偷走有线口）。
7. **`07_setup_media_route.sh`** —— 策略路由：把 `.126` 源地址的流量钉死走 `wlan1`。
8. **`08_net_test_video.sh` / `09_net_test_audio.sh`** —— 历史版本（同机 netns 接收，**已撤回、不作基线**）；价值是看接收端管线怎么写，以及"为什么同机接收不能算 STA→AP 基线"。
9. **`10_recon_and_evidence.md`** —— 只读侦察命令和四条硬证据，用于确认媒体真走了无线。

---

## 四、运行环境与依赖

| 环境 | 用途 | 依赖 |
|---|---|---|
| Pi 5（Debian 13，GStreamer 1.26.2） | 跑 Shell 脚本、`gst-launch`、`rtp_probe.py` | `python3`、GStreamer RTP/音频/视频插件 |
| Windows 本机 | 跑 `03_pcap_rtp_rebuild.py` 解析 pcap | `scapy`、`av`（PyAV，可选） |

- `01_rtp_header_demo.py`：纯标准库，`python` 直接跑，127.0.0.1 自收自发。
- `02_rtp_probe.py`：纯标准库；用法 `python3 rtp_probe.py <端口> <秒数>`。
- `03_pcap_rtp_rebuild.py`：`pip install scapy av`；pcap 路径可改命令行参数。

---

## 五、概念速查

- **payloader / depayloader**：把编码后的视频/音频切片塞进 RTP 包（pay），接收端再拼回来（depay）。H.264 对应 `rtph264pay/rtph264depay`，Opus 对应 `rtpopuspay/rtpopusdepay`。
- **FU-A**：一帧太大、超过 MTU 时，H.264 NAL 被切成多个 RTP 包（RFC 6184）；接收端按 S/E 位重组。
- **STAP-A**：多个小 NAL 合进一个 RTP 包。
- **jitter buffer（`rtpjitterbuffer`）**：接收端缓存一小段时间，把乱序/抖动的包排好序再交给解码器。
- **SSRC**：同步源标识；视频一路、音频一路，靠 SSRC 区分，不靠端口。
- **A-MSDU 聚合**：AP 无线口抓包时，一个抓包记录可能装着多个 RTP 包，序号会"跳变"，所以 AP 侧 pcap 不能直接算丢包率。
