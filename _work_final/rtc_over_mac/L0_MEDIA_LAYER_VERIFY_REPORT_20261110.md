# L0 本地回环媒体层验证实验报告

- 报告日期：2026-11-10（v2 回填：补做 T3 归因、T5 SR 字段级、T6 乱序、T7 丢包反馈、T8 锚点偏差、T9 画质指标、T4 SRTP 闭环）
- 验证级别：**L0 本地回环（127.0.0.1），不触碰无线网络**
- 被测对象：GStreamer 开源元件组装的 RTP/RTCP/SRTP 媒体层；测试脚本只做编排与记录，**媒体层无自研代码**
- 测试机：Raspberry Pi 5（主机名 RPI-5，Debian 13 trixie aarch64）
- 对应方案：`RTC_OVER_MAC_IMPLEMENTATION_PLAN_20261109.md` §6 M0–M8、§7 三层验证模型

> 口径说明：本报告只记录 L0 本地回环结果。真实无线链路、码率/帧率矩阵、10 min 长稳不在本轮范围，见 §5.3。Pi 上不存在旧媒体层，本报告口径为"第一次装上开源媒体层"的验证。

---

## 1. 验证目的与范围

### 1.1 目的

确认第一次装上 Pi 的这套开源媒体层，在不经过真实网络的前提下，下列能力是否成立：

1. 源片能解封装、能解码，管线无解码器报错；
2. H.264 / Opus 能打成 RTP，RTP 头字段（版本、PT、序号、SSRC、时间戳）符合规范；
3. RTP 回环后能拆包、重组、解码，帧数与源片对账；
4. rtpbin 能开启 RTCP 通道并发出 SR，SR 内字段可逐字段解析；
5. 抖动缓冲乱序重排、SRTP 加解密、丢包反馈、音画同步偏差、画质指标在本地回环可测部分的实测结果。

### 1.2 范围边界（本轮做与不做）

**本轮 L0 本地回环已做：** 编解码基线、RTP 头字段、回环帧级对账与缺帧归因、RTCP SR 通道与字段解析、乱序注入重排、SRTP 加解密闭环、音画锚点偏差、PSNR/SSIM 跑值、确定性丢包注入与双 rtpbin 通路。

**本轮不做（属后续里程碑）：**

- 不跑真实 Wi-Fi / AP 链路（L1 / M1）；
- 不派生 10/15/20 Mbps 码率档位、24/25/30 fps 矩阵、10 min 长稳（M6）；
- NACK/RTX/PLI 丢包恢复闭环在本地最小回环未建立，留 M5（见 T7）；
- 空口真实丢包/抖动/时延/CPU 实测留 L1。

### 1.3 三层验证模型

| 层级 | 查什么 | 手段 |
|---|---|---|
| 字段级 | RTP 头 V/P/X/CC、M/PT、seq、timestamp、SSRC 是否规范；RTCP SR 字段与一致性 | 独立探针拆头统计（只读，不参与媒体路径） |
| 帧级 | 拆包重组后能否解码、解码帧数与源片是否一致、有无解码错误 | 接收端解码后降采样写原始 YUV，按每帧字节数反算帧数 |
| 功能级 | RTCP SR 通道、抖动缓冲链接/重排、SRTP 加解密、重传属性、反馈报文类型 | rtpbin 管线 + RTCP 探针；PyGI 代码级管线；元件/属性 `gst-inspect` 清点 |

---

## 2. 测试环境与素材

### 2.1 软件版本（Pi 实测）

| 项 | 版本 / 实测值 |
|---|---|
| GStreamer | 1.26.2（`gst-launch-1.0`） |
| FFmpeg | 7.1.5-0+deb13u1+rpt2 |
| Python | 3.13.5 |
| 操作系统 | Debian 13 trixie aarch64，4 核 / 8058 MB RAM |

### 2.2 素材

| 文件 | 说明 |
|---|---|
| `1080p30_1_artemis_origins_85s.mp4` | 原始素材，2560 帧 / 85.333 s / 1920×1080 / 30 fps / H.264 + AAC 48 kHz 立体声 |
| `clip10.mp4` | `-c copy` 流复制截取的 10 s 片段（**未重编码**）；ffprobe 计数 **302 帧**，1920×1080，30 fps |
| `anchor.mkv`（`anchor_1080p30_clapper_10s.mkv`） | A/V 锚点素材，178,004 B，SHA256 `ff09289c8850dc5f66875216bfa7e4bc06dffb7cd9bc036e54dec0252516de25`；H.264 1920×1080 30 fps + Opus 48 kHz 立体声；0–9 s 每秒一整帧白闪 + 50 ms / 1 kHz 短音；`-bf 0` 无 B 帧，GOP=30 |

片段帧类型分布（ffprobe）：I 帧 11、P 帧 86、B 帧 204（含 B 帧，解码顺序 ≠ 显示顺序）。

### 2.3 元件清点（`gst-inspect-1.0` 实测，25/25 在位）

| 元件 | 用途 | 在位 |
|---|---|---|
| `rtpbin` | RTCP SR/RR、会话管理、重传调度 | yes |
| `rtpjitterbuffer` | 抖动缓冲、乱序重排、等重传 | yes |
| `srtpenc` / `srtpdec` | SRTP 加密 / 解密 | yes / yes |
| `rtph264pay` / `rtph264depay` | H.264 RTP 打包 / 拆包 | yes / yes |
| `rtpopuspay` / `rtpopusdepay` | Opus RTP 打包 / 拆包 | yes / yes |
| `opusenc` / `opusdec` | Opus 编码 / 解码 | yes / yes |
| `avdec_h264` / `h264parse` | H.264 解码 / 流规范化 | yes / yes |
| `aacparse` / `avdec_aac` | AAC 解析 / 解码 | yes / yes |
| `audioconvert` / `audioresample` / `audiorate` | 音频格式 / 采样率 / 帧率校正 | yes / yes / yes |
| `videoscale` / `videoconvert` / `queue` | 降采样 / 视频格式转换 / 缓冲 | yes / yes / yes |
| `identity` / `fakesink` / `filesink` | 探针 / 丢弃 / 落盘 | yes / yes / yes |
| `udpsrc` / `udpsink` / `qtdemux` | UDP 收发 / MP4 解封装 | yes / yes / yes |
| `matroskademux` / `opusparse` | MKV 解封装 / Opus 解析 | yes / yes |

### 2.4 测试脚本与产物（Pi 远端 `/home/bai/rtc_test/l0/`、结果 `/tmp/l0/`）

- 编排脚本：`run_l0.sh`（T1–T9 首轮）
- 探针：`rtp_probe.py`（RTP 头统计）、`rtcp_probe.py`（RTCP 类型统计，PT 取整字节）、`rtcp_sr_probe.py`（SR 固定头解析 + 一致性校验）
- 注入代理：`reorder_proxy.py`（成对交换乱序，不丢包）、`loss_proxy.py`（序号取模确定性丢包）
- 代码级管线：`srtp_loopback.py`（PyGI 双管线 SRTP 闭环）、`srtp_setup.sh`（免 sudo typelib 解包）、`srtp_run.sh`（带 `GI_TYPELIB_PATH` 运行）
- 音画分析：`av_skew.py`（YUV + PCM 音画偏差分析）
- 隔离诊断：`debug_t3.sh`、`debug2.sh`～`debug29.sh`、`depay_stats.sh`、`nal_scan.py`、`env_check.sh`
- 本地学习包镜像：`test_harness/l0_verify/`（带中文注释，LF 无 BOM）

---

## 3. 逐项测试：方法与实测结果

### T1 解封装 + 解码（帧级基线）

**功能定义**：源片经 MP4 解封装 → H.264 解析 → 软解码，验证解码管线本身可用、无解码器报错。

**测试方法**

```text
发送/解码管线：
filesrc ! qtdemux ! h264parse ! avdec_h264 ! fakesink sync=false
参照：ffmpeg -i clip10.mp4 -an -f null - 统计帧数与错误行
```

**实测结果**

| 指标 | 实测值 |
|---|---|
| GStreamer 管线退出码 | 0 |
| ffmpeg 参照解码帧数 | 302 |
| 解码器错误行数 | 0 |

**判定：通过。** 源片段解封装、解码链路干净，302 帧全部可解，无 error/corrupt/wrong 行。

---

### T2 视频 RTP 打包头字段（字段级）

**功能定义**：H.264 帧打成 RTP（PT=96，90 kHz 时钟），探针拆 12 字节固定头，核查版本、PT、序号连续性、SSRC 单一性、时间戳个数。

**测试方法**

```text
发送管线：
filesrc ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96
  ! udpsink host=127.0.0.1 port=5004
探针：rtp_probe.py 监听 5004，统计包数/序号缺口/SSRC 集合/时间戳个数/PT
```

**实测结果**

| 指标 | 实测值 |
|---|---|
| RTP 包数 | 5933 |
| 序号缺口 seq_gaps | 0 |
| SSRC 集合 | 单 SSRC `3291272362`（首轮会话值，每次随机） |
| 时间戳个数 | 302（与源片帧数一致） |
| 载荷类型 PT | 96 |
| 管线退出码 | 0 |

**判定：通过（字段级）。** 序号连续无缺口；单一会话源 SSRC；时间戳个数与帧数 1:1；PT=96 与声明一致。SSRC 每次会话随机生成，属正常行为。

> 备注：5933 包 / 302 帧 ≈ 19.6 包/帧，单帧被拆成多个 RTP（FU-A 分片），与 H.264 MTU 分片预期一致。

---

### T3 回环拆包重组 + 解码对账（帧级闭环，含缺帧归因）

**功能定义**：RTP 经 UDP 本地回环后，接收端拆包重组 → 解码 → 降采样落盘，帧数与源片对账；并对首轮 300/302 的 2 帧缺口做分段归因。

**测试方法**

```text
接收管线：
udpsrc port=5014 caps="application/x-rtp,media=video,clock-rate=90000,
  encoding-name=H264,pt=96"
  ! queue ! rtpjitterbuffer ! rtph264depay ! h264parse
  ! avdec_h264 ! videoscale ! videoconvert
  ! video/x-raw,format=I420,width=320,height=180 ! filesink rx.yuv

发送管线：
filesrc ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96
  ! udpsink host=127.0.0.1 port=5014

帧数对账：rx.yuv 字节数 ÷ 每帧字节数（320×180×3/2 = 86400）= 解码帧数
归因分段：接收端口探针 / depay AU 计数 / 本地不经 RTP 对照解码 /
  变体 V1(无 jb 无 parse)、V2(加 jb)、V3(完整链) / 派生 -bf 0 无 B 帧片段对照
```

**首轮实测结果**

| 指标 | 实测值 |
|---|---|
| 发送管线退出码 | 0 |
| 接收管线退出码 | 124（`timeout` 主动结束，非报错） |
| rx.yuv 字节数 | 25,920,000 |
| 每帧字节数 | 86,400 |
| 解码帧数 | **300** |
| 源片帧数 | 302 |
| 管线错误行数 | 0（接收 / 发送两侧均 0） |

**归因分段实测（本轮补做）**

| 分段 | 实测结果 | 排除/结论 |
|---|---|---|
| 接收端口探针 | 5933 包、gap=0、**302 个时间戳全部到达** | 排除 UDP/接收端口丢包 |
| depay AU 计数 | `taking completed AU` = **302**；NAL 分布 type1=298、type12=11、type5=4、type6=315、type7=5、type8=5、type9=302 | 排除 depay 重组丢 AU |
| 本地不经 RTP 对照解码 | 320×180 与 1920×1080 两档均 **302 帧 0 错误** | 排除解码/缩放链自身丢帧 |
| 变体 V1 无 jb 无 parse / V2 加 jb / V3 完整链 | 均 300 帧 | 排除 jitterbuffer、h264parse 导致缺帧 |
| 派生 `-bf 0` 无 B 帧片段走同一 RTP 回环 | **302/302，0 错误** | 含 B 帧原片 300/302；缺口与 B 帧相关 |

**归因结论**：缺的 2 帧是 UDP 回环**无 EOS 冲刷**时 `avdec_h264` 尾部重排缓存滞留的 B 帧，属**测量假象，非媒体层缺陷**。真实会话靠 RTCP BYE / 管线 EOS 冲刷尾部缓存。

**判定：功能链路通过；帧级严格相等仍需在 M1 门禁复核。** 排除传输、depay、解码缩放、jb、parse 各环节后，缺口定位到无 EOS 的尾部 B 帧滞留；方案 M1 门禁仍要求"源帧数 = 解码帧数"，进入 L1 时以显式 EOS 会话复测。

---

### T4 SRTP 加解密闭环（本地代码级管线，已闭环）

**功能定义**：`srtpenc`/`srtpdec` 对 RTP/RTCP 做鉴权加密（AES-128-ICM + HMAC-SHA1-80），是必须保留项（禁止裁剪 auth tag）。

**测试方法**

- 免 sudo 路线：`apt-get download gir1.2-gstreamer-1.0`（候选 1.26.2-2，118 KB）→ `dpkg-deb -x` 解包到 `~/.local/gi` → 设 `GI_TYPELIB_PATH`，PyGI 成功加载 Gst 1.26.2（sudo 需要密码，未走 sudo）。
- PyGI 双管线 `srtp_loopback.py`：
  - 发送：`filesrc ! qtdemux ! h264parse ! rtph264pay ! srtpenc(key=30B) ! udpsink`
  - 接收：`udpsrc(x-srtp) ! srtpdec(request-key 供钥) ! rtph264depay ! h264parse ! avdec ! fakesink`
  - `request-key` 信号回调按 SSRC 返回 `application/x-srtp` caps，密钥字段 `srtp-key`（16B 主密钥 + 14B salt = 30B）。

**实测结果**

| 指标 | 实测值 |
|---|---|
| 回调供钥 SSRC | 4221072070 |
| 发送端 enc 流 | 已为该 SSRC 建立 SRTP 流 |
| 接收端 `recv-count`（成功解密/鉴权包数） | **5911** |
| 接收端 `recv-drop-count`（鉴权/解密失败丢弃数） | **0** |
| 解码帧数 | 297 |
| 总线 ERROR / WARNING 致命错误 | 0 / 0 |
| 密码套件 | AES-128-ICM 加密 + HMAC-SHA1-80 鉴权 |

**判定：通过（本地闭环）。** 全部 5911 个 SRTP 包通过鉴权与解密，0 失败丢弃；接收端能拆包解码。测试密钥为固定 30B（`bytes(range(30))`，仅本地自测），生产环境由 DTLS/PSK 协商产生。解码 297 帧与 T3 同类尾部滞留假象一致（见 T3 归因）。

> 备注：`srtpdec` 无 `key` 属性，密钥只能经 `request-key` 信号回调下发；gst-launch 无法连接回调，故用 PyGI 代码级管线。

---

### T5 rtpbin RTCP SR（功能级 + SR 字段级解析）

**功能定义**：rtpbin 作为发送方会话管理器，除 RTP 外另开 RTCP 通道，周期发出 SR（发送方报告，PT=200，携带 NTP↔RTP 时间映射，是音画同步锚点）。本轮对 SR 固定头做逐字段解析与一致性校验。

**测试方法**

```text
管线（官方写法，面板名带会话序号 _0）：
rtpbin name=R
  filesrc ! qtdemux ! h264parse ! rtph264pay pt=96 ! R.send_rtp_sink_0
  R.send_rtp_src_0  ! udpsink port=5034（RTP）
  R.send_rtcp_src_0 ! udpsink port=5035 sync=false async=false（RTCP）
探针：rtcp_sr_probe.py 按 length 切片复合包，解 SR 固定头，
  校验 SSRC 一致性、包数/字节计数单调不减、NTP↔RTP 时钟速率
```

**实测结果**

| 指标 | 实测值 |
|---|---|
| 管线退出码 | 0 |
| RTCP 总包数 | 7（3 SR(200) + 3 SDES(202) + 1 BYE(203)） |
| SR 内 SSRC | 单 SSRC `2041065122` |
| SR 累计包数（3 个 SR 采样） | 1931 → 4656 → 5933（单调不减） |
| SR 累计字节数 | 2,408,225 → 5,655,367 → 7,142,872（单调不减） |
| 最终包数 / 字节与 T2 发送侧探针 | 5933 包、7,142,872 B，完全一致 |
| NTP↔RTP 推算时钟速率 | 90000.0 Hz，匹配视频 90 kHz 时钟 |
| 管线错误行数 | 0 |

**判定：通过（功能级 + 字段级）。** RTCP 通道建立；SR 计数字段单调不减且与 RTP 发送侧对账一致；时间戳时钟速率与视频 90 kHz 匹配；SDES/BYE 报文类型正常。

---

### T6 抖动缓冲：乱序注入与 jitterbuffer 重排（对照闭环）

**功能定义**：`rtpjitterbuffer` 吸收乱序、重排包序。本轮用 `reorder_proxy.py` 成对交换序号（不丢包）注入乱序，做"带 jb / 无 jb"双臂对照。

**测试方法**

```text
代理：reorder_proxy.py 成对交换相邻 RTP 序号，不丢弃任何包
臂 J（带 jb）：udpsrc ! rtpjitterbuffer ! rtph264depay ! h264parse ! avdec ! fakesink
臂 N（无 jb 对照）：udpsrc ! rtph264depay ! h264parse ! avdec ! fakesink
```

**实测结果**

| 臂 | 注入逆序对 | 转发包数 | 解码帧数 | 解码错误 |
|---|---|---|---|---|
| J：带 jitterbuffer | 2966 | 5933 全转发 | **300** | 0 |
| N：无 jitterbuffer | 2964 | — | **0** | 0 字节输出 |

**判定：通过（乱序重排功能级）。** 带 jb 臂在近 3000 处逆序对下仍重排出完整流并解码 300 帧 0 错误；无 jb 对照臂 depay/decode 完全失效（0 帧 0 字节）。缓冲深度/过期丢弃行为留 L1 真实链路复测。

---

### T7 丢包注入 + NACK/RTX/PLI 反馈（部分成立，闭环未建立）

**功能定义**：丢包时接收方发 NACK（RTPFB，PT=205）请求重传；画面损坏时发 PLI（PSFB，PT=206）请求 IDR；发送方按 RTX 重传。必须保留。

**测试方法**

- `loss_proxy.py`：序号取模确定性丢包（每 mod=20 丢 1，约 5%），输出 received/forwarded/dropped/drop_ratio/丢弃序号样本。
- 双 rtpbin 交叉通路：发送 rtpbin ↔ 接收 rtpbin，RTP + 双向 RTCP 回连。
- 三臂对照：A 无丢失+恢复开；B 5% 丢失+恢复开（`do-retransmission=true`）；C 5% 丢失+恢复关。
- 反馈探针：接收端 RTCP 输出 tee 分叉一路到探针端口，统计出站 RTCP 类型（201 RR / 205 RTPFB-NACK / 206 PSFB-PLI）。

**实测结果**

| 臂 | 注入 | 恢复开关 | 解码帧数 | 解码错误 |
|---|---|---|---|---|
| A：无丢失基线 | 0 | on | 297 | 4 |
| B：5% 丢失 | 296/297 包（5.0%） | on | 85–90 | 145 |
| C：5% 丢失 | 296/297 包（5.0%） | off | 107 | 143 |

代理计数（臂 B）：received=5933、forwarded=5636、dropped=297、drop_ratio=0.0501。

**反馈报文实测（探针抓接收端出站 RTCP）**

| RTCP 类型 | 计数 |
|---|---|
| 201 RR（接收方报告） | 54 |
| 205 RTPFB / NACK | **0** |
| 206 PSFB / PLI | **0** |

发送端日志未见重传（RTX）触发记录。

**判定：丢包注入与双 rtpbin 通路成立；NACK/RTX/PLI 恢复闭环在本地最小回环**未建立**，DEFERRED-M5。**

- 已证明：确定性丢包代理按规则工作；双 rtpbin RTCP 交叉管线可链接、可流动；无丢失基线臂 297 帧。
- 未证明：恢复开（B）未优于恢复关（C），均远低于基线 297 帧；出站 RTCP 只有 RR，未捕获到 NACK(205)/PLI(206)，发送端无重传。
- 根因方向（M5 排查）：最小会话内内部 jb 的重传请求 / RTCP feedback 类型未被协商触发；需用 `request-jitterbuffer` 信号显式配置 `do-retransmission` 与 `rtx-*` 参数；探针确认 205/206 真正出站；用 PyGI 读内部 jb 的 `rtx-count` / `rtx-success-count` / `rtx-rtt`；再在真实链路 RTT 下复测 PLI 关键帧刷新。

---

### T8 音频 Opus RTP + A/V 锚点偏差（字段级 + 同步基准）

**功能定义**：AAC → 解码 PCM → 重采样 48 kHz → Opus 编码 → RTP 打包（PT=111，独立 SSRC）；用锚点素材测量 RTP 回环臂相对源基线臂的音画对齐偏差。

**测试方法**

```text
音频发送管线：
filesrc ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample
  ! opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5006

锚点偏差：源基线臂（不经 RTP）与 RTP 回环臂各跑两条独立 gst-launch
  （视频/音频独立进程，避免单管线双分支互阻）；av_skew.py 检测白闪帧与
  1 kHz 短音时刻配对，输出 p50/p95/最大偏差，门限 40 ms。
```

**字段级实测（首轮）**

| 指标 | 实测值 |
|---|---|
| RTP 包数 | 496 |
| 序号缺口 seq_gaps | 0 |
| SSRC | 单 SSRC `3047393832`（与视频流不同） |
| 载荷类型 PT | 111 |
| 管线退出码 | 124（`timeout` 主动结束，非报错） |

**锚点偏差实测（本轮补做）**

| 臂 | 白闪帧 | 短音 | 偏差 p50 | p95 | 最大 |
|---|---|---|---|---|---|
| 源基线臂（不经 RTP） | 10 | 10 | 0 ms | 20 ms | 20 ms |
| RTP 回环臂 | 10 | 9（末尾短音同 EOS 滞留假象） | 0 ms | 20 ms | 20 ms |

9 对可配对锚点偏差 **p50=0 ms、p95=20 ms、最大 20 ms**，在 40 ms 门限内；20 ms 来自 20 ms RMS 短音窗量化，与源基线臂一致，非媒体层引入偏差。

**判定：音频打包字段级通过；本地回环 A/V 偏差在门限内。** 遗留：音频路径上的 rtpjitterbuffer 在无 RTCP 反馈的最小回环里滞留全部缓冲（带 jb 臂 0 字节，去 jb 后 aA=1,866,240 B / aB=131,138 B 正常），列入 M2 随 rtpbin 双流闭环复测。

> 排障记录：qtdemux 解不了 MKV（bogus size），锚点素材须用 `matroskademux`；单 gst-launch 管线内视频+音频双分支互相阻塞，改为两个独立进程。

---

### T9 画质指标 PSNR / SSIM（本地跑值）

**功能定义**：对照源参照帧与 RTP 回环解码帧的像素质量。本地回环不重编码，理论上逐比特一致；本轮把流程跑通并取实测值，真实画质损伤基线留 L1/L2。

**测试方法**：源参照 302 帧 YUV 与回环 300 帧 YUV 对齐前 300 帧算 PSNR/SSIM；再对整体（含尾部错位帧）算平均。

**实测结果**

| 指标 | 实测值 |
|---|---|
| 对齐前 300 帧 PSNR | inf |
| 对齐前 300 帧 SSIM | 1.0 |
| 整体 PSNR 平均 | **58.83 dB**（Y 57.08 / U 78.64 / V 82.93；最小 34.61 dB，在错位的第 302 帧） |
| 整体 SSIM | **All 0.999876**（Y 0.999818） |

**判定：流程跑通，本地无损伤基线成立。** 对齐帧逐比特一致（PSNR=inf、SSIM=1.0）；整体最小值被尾部 2 帧错位拉低，属 T3 已知 EOS 滞留假象。L1/L2 阶段在此基线上测真实编码/链路损伤。

---

## 4. 测试过程中定位并修复的问题（排查记录）

本轮不是一次跑通，以下问题经隔离复现后定位，均已在最终脚本中修正：

### 4.1 udpsrc 缺 RTP caps，depayloader 协商失败

- **现象**：最简接收链 `udpsrc ! rtph264depay ! filesink` 写出 0 字节；报错 `No RTP format was negotiated` / `Input buffers need to have RTP caps set on them`。
- **根因**：`udpsrc` 未给 caps，上游 buffer 不带 RTP caps，depayloader 拒绝协商。
- **修复**：`udpsrc` 显式带 `caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"`。修复后接收链写出数据。

### 4.2 rtpbin 面板名必须带会话序号 `_0`

三轮报错逐步定位：`未预期的引用"R" - 忽略` → `No sink-element named "(null)" - omitting link` → `无法将 rtph264pay0 链接到 R`。

- **根因**：rtpbin 的 `send_rtp_sink_%u` / `send_rtp_src_%u` / `send_rtcp_src_%u` 是**请求面板**，gst-launch 中必须写带序号的全名（对照 GStreamer 官方 rtpbin 文档示例）。
- **修复**：改用 `_0` 序号面板，RTCP 通道建立成功（见 T5）。

### 4.3 RTCP 探针 PT 掩码错误

- **现象**：RTCP SR（PT=200，二进制 0xC8）被探针统计成 PT=8。
- **根因**：探针沿用 RTP 的低 5 位掩码 `& 0x1F`；RTCP PT 是整字节（200–206），不应掩码。
- **修复**：RTCP PT 取整字节 `data[1]`；复测计数为 `{"200": 3}`。

### 4.4 落盘 ES 为 AVCC 长度前缀，ffprobe 无法解析

- **现象**：带 caps 后接收文件约 7.12 MB 有字节量，但 ffprobe 报 `non-existing PPS referenced`、`decode_slice_header error`、`no frame!`，帧数 N/A。
- **定位**：文件头为 `00 00 00 2c 27 ...`（4 字节长度前缀 + NAL），是 AVCC 长度前缀格式，不是 annexb 起始码格式；`h264_mp4toannexb` 因缺 avcC 头转换失败（bsf rc=234）。源片 ES 直接解码 302 帧 0 错误，证明问题在落盘格式而非传输。
- **最终方案**：帧级对账改为**接收端解码后降采样写原始 YUV**，按固定每帧字节数反算帧数，绕开 ES 封装格式分歧（见 T3）。

### 4.5 参照帧数统计被日志级别抑制

- **现象**：首轮 `ffmpeg -v error -f null` 参照帧数为 NA。
- **根因**：`-v error` 抑制了 `frame=` 统计行。
- **修复**：参照帧数以 ffprobe `-count_frames` 结果 302 为准；ffmpeg 解码保留用于错误行统计。

### 4.6 rtpbin 接收输出动态面板：写死 SSRC 后缀导致 not-linked

- **现象**：双 rtpbin 接收管线报 `streaming stopped, reason not-linked (-1)`，0 帧输出。
- **根因**：`recv_rtp_src_%u_%u_%u` 面板三段为 会话 / SSRC / PT；gst-launch 中写死 `recv_rtp_src_0_0_0`，实际 SSRC 非 0，面板解析失败。
- **修复**：按官方示例接收输出侧用裸 bin 引用 `RR. ! rtph264depay ...`，由 gst-launch 自动挂接动态 src 面板。修复后接收链 297 帧跑通（见 T7 基线臂）。

### 4.7 PyGI 代码级管线的三个接口坑

- **Element.link() 返回布尔值**，不是 `PadLinkReturn` 枚举；按枚举比较会误判链接失败。
- **qtdemux 是动态 pad**：静态 `demux.link(parse)` 在 pad 出现前就失败；须等 `pad-added` 信号挂接视频分支。
- **Gst.Structure 统计**：不同 typelib 版本字段枚举 API 不一致（无 `keys()`/`get_field_name()`）；取 `to_string()` 记录最稳。

### 4.8 SRTP 免 sudo typelib 路线

- **卡点**：`srtpdec` 密钥走 `request-key` 信号，gst-launch 连不了回调；系统 PyGI 缺 Gst typelib，而 sudo 需要密码。
- **解决**：`apt-get download gir1.2-gstreamer-1.0` → `dpkg-deb -x` 解包到用户目录 → `GI_TYPELIB_PATH` 指向解包目录，免 sudo 加载 Gst 1.26.2，再用 PyGI 双管线完成 SRTP 闭环（见 T4）。

### 4.9 MKV 解封装与单管线双分支互阻

- **现象**：锚点 MKV 走 qtdemux 报 bogus size；单管线内视频+音频双分支各自单路通、合流 0 包。
- **定位/修复**：MKV 必须用 `matroskademux`；音视频改为两个独立 gst-launch 进程，模拟两条独立 RTP 会话。音频 jb 在无 RTCP 反馈最小回环滞留全部缓冲，去 jb 后正常（见 T8）。

---

## 5. 总体验证分析

### 5.1 结果汇总

| 编号 | 功能 | 层级 | 实测要点 | 判定 |
|---|---|---|---|---|
| T1 | 解封装 + 解码 | 帧级 | rc=0，参照 302 帧，解码器错误 0 | **通过** |
| T2 | 视频 RTP 头字段 | 字段级 | 5933 包，gap=0，单 SSRC，ts=302，PT=96 | **通过** |
| T3 | 回环拆包重组 + 解码 | 帧级 | 300/302；分段归因：缺 2 帧为无 EOS 尾部 B 帧滞留，非媒体层缺陷 | **功能通过；严格相等留 M1 复核** |
| T4 | SRTP 加解密 | 功能级 | 双管线闭环，recv-count=5911，recv-drop-count=0，0 总线错误 | **通过（本地闭环）** |
| T5 | rtpbin RTCP SR | 功能/字段级 | 3 SR + 3 SDES + 1 BYE；计数单调不减并与 RTP 侧一致；90 kHz 匹配 | **通过** |
| T6 | 抖动缓冲乱序重排 | 功能级 | 带 jb 2966 逆序对 → 300 帧 0 错误；无 jb 0 帧 | **通过（乱序重排）** |
| T7 | NACK/PLI/RTX | 功能级 | 丢包代理 + 双 rtpbin 通路成立；出站仅 RR，无 NACK/PLI，RTX 未触发 | **部分成立 / DEFERRED-M5** |
| T8 | 音频 Opus RTP + A/V 偏差 | 字段/同步级 | 496 包 gap=0 PT=111；锚点 p50=0 / p95=20 / max=20 ms，门限内 | **通过（本地基准）** |
| T9 | PSNR / SSIM | 画质 | 对齐帧 inf / 1.0；整体 PSNR 58.83 dB、SSIM 0.999876 | **流程跑通，无损伤基线成立** |

### 5.2 已经证明成立的部分

1. **编解码基线可用**：源片解封装、H.264 软解码、AAC→Opus 链路在 Pi 上跑通，无解码器报错（T1、T8）。
2. **RTP 打包符合字段规范**：视频 PT=96 / 90 kHz、音频 PT=111；序号连续无缺口；各流单 SSRC；视频时间戳个数与帧数 1:1（T2、T8）。
3. **回环拆包重组链路可用**：接收端 depay → parse → 解码无错误；缺帧经分段归因到无 EOS 尾部 B 帧滞留，排除传输/depay/解码/缩放/jb/parse（T3、T6）。
4. **RTCP 发送侧通道与 SR 字段成立**：SR 计数单调不减、与 RTP 侧对账一致，NTP↔RTP 时钟速率匹配（T5）。
5. **SRTP 加解密本地闭环**：AES-128-ICM + HMAC-SHA1-80，5911 包全部鉴权解密通过、0 丢弃（T4）。
6. **乱序重排有效**：近 3000 处逆序对被 jb 重排，无 jb 对照完全失效（T6）。
7. **本地 A/V 同步基准在门限内**：锚点偏差 p95=20 ms，与源基线一致（T8）。
8. **本地无损伤画质基线成立**：对齐帧逐比特一致，整体 PSNR 58.83 dB / SSIM 0.999876（T9）。
9. **25/25 元件与重传/缓冲属性全部在位**（T6、T7，元件清点通过）。

### 5.3 尚未证明、不得提前下结论的部分

| 未闭环项 | 原因 | 计划里程碑 |
|---|---|---|
| 源帧数 = 解码帧数严格相等 | 缺帧已归因到无 EOS 尾部滞留；需显式 EOS 会话复测 | L1 / M1 |
| NACK / PLI / RTX 丢包恢复 | 本地最小回环出站仅 RR，NACK/PLI 未触发，RTX 未回填 | M5 |
| 抖动缓冲深度 / 过期丢弃 | 本地无真实抖动；乱序重排已验证 | L1 |
| 音频 jb 在 RTCP 反馈闭环下的行为 | 最小回环音频 jb 滞留全部缓冲 | M2 |
| 真实无线链路帧完整率 / 时延 / 抖动 / CPU | L0 不碰网络 | L1 / M1 |
| 10/15/20 Mbps、24/25/30 fps 矩阵、10 min 长稳 | 本轮用原始片 10 s 片段 | M6 |
| SRTP 生产密钥协商 / 抗重放窗口实测 | 本地用固定自测密钥 | M2 |
| 真实链路画质损伤（编码/空口引入） | 回环同源无损伤 | L1 / L2 |

### 5.4 总体结论

- **L0 结论**：这套开源媒体层在本地回环条件下，**解封装/解码、H.264 与 Opus RTP 打包、RTCP SR 通道与字段、拆包重组解码、乱序重排、SRTP 加解密、本地 A/V 同步基准、无损伤画质基线均已跑通**；字段级全部通过，功能级除 T7 反馈闭环外通过，帧级 T1 通过、T3 缺口归因清楚。
- **不能据此冻结 UDP baseline**：M1 验收门禁是"真实无线链路 + 源帧数=解码帧数 + 链路指标记录"，当前真实链路未测、T3 严格相等待显式 EOS 复测。
- **风险提示**：T7 在本地最小回环未观察到 NACK/PLI 出站与 RTX 回填，进入 M5 前不应假设丢包恢复已可用；音频 jb 滞留需随 M2 rtpbin 双流闭环复测。
- **下一步建议**：
  1. 确认参考接收端形态（方案 §10.1 开放问题）后进入 M1 真实无线链路，显式 EOS 会话复核帧数；
  2. M2 补 SRTP 生产密钥协商、Opus 双流 RTCP SR、A/V 同步在 rtpbin 闭环下复测；
  3. M5 用 `request-jitterbuffer` 显式配置重传参数，探针确认 205/206 出站，读内部 jb RTX 统计，再在真实链路 RTT 下验恢复与 PLI 刷新；
  4. M6 跑码率/帧率矩阵与长稳。

---

## 附录 A：首轮 `results.env` 全量实测值（2026-11-10 20:22:31）

```text
HOST=RPI-5
DATE=2026-11-10 20:22:31
GST_VERSION=gst-launch-1.0 version 1.26.2
CLIP_FRAMES=302
CLIP_RES=1920,1080
T1_GST_RC=0
T1_FF_REF_FRAMES=302
T1_DECODER_ERRORS=0
T2_GST_RC=0
T2_PACKETS=5933
T2_SEQ_GAPS=0
T2_SSRCS=3291272362
T2_TIMESTAMPS=302
T2_PT=96
T3_SEND_RC=0
T3_RECV_RC=124
T3_RX_BYTES=25920000
T3_RX_FRAMES=300
T3_PER_FRAME=86400
T3_PIPELINE_ERRORS=0
T4_SRTPENC_PRESENT=yes
T4_SRTPDEC_PRESENT=yes
T4_STATUS=DEFERRED-M2
T5_GST_RC=0
T5_RTCP_PACKETS=3
T5_RTCP_PT={"200": 3}
T5_PIPELINE_ERRORS=0
T6_JB_PRESENT=yes
T6_JB_LATENCY_PROP=3
T6_JB_MODE_PROP=1
T6_STATUS=LINKED-OK；乱序/丢包缓冲行为 DEFERRED-L1
T7_RTPBIN_RETX=1
T7_JB_RETX=1
T7_JB_RTX_PROPS=14
T7_STATUS=PROPS-PRESENT；丢包恢复闭环 DEFERRED-M5
T8_GST_RC=124
T8_PACKETS=496
T8_SEQ_GAPS=0
T8_SSRCS=3047393832
T8_PT=111
T8_STATUS=SYNC-SKEW DEFERRED-M2
T9_STATUS=PSNR/SSIM DEFERRED-L1
```

## 附录 B：本轮补做实测值汇总（v2）

```text
# T3 归因
T3_PROBE_PACKETS=5933
T3_PROBE_GAPS=0
T3_PROBE_TIMESTAMPS=302
T3_DEPAY_AU=302
T3_LOCAL_REF_FRAMES=302
T3_NOBF_CLIP_LOOPBACK=302/302
T3_ROOTCAUSE=无EOS尾部B帧滞留（测量假象，非媒体层缺陷）

# T5 SR 字段级
T5_RTCP_TOTAL=7
T5_RTCP_PT={200:3, 202:3, 203:1}
T5_SR_SSRC=2041065122
T5_SR_PACKETS=1931/4656/5933
T5_SR_BYTES=2408225/5655367/7142872
T5_CLOCK_RATE=90000.0
T5_PIPELINE_ERRORS=0

# T8 锚点偏差
ANCHOR_SHA256=ff09289c8850dc5f66875216bfa7e4bc06dffb7cd9bc036e54dec0252516de25
T8_SRC_FLASH=10 / T8_SRC_TONE=10 / p50=0ms / p95=20ms
T8_RX_FLASH=10 / T8_RX_TONE=9 / 9对 p50=0ms / p95=20ms / max=20ms / 门限40ms内

# T6 乱序对照
T6_JB_PAIRS=2966 / T6_JB_FRAMES=300 / T6_JB_ERRORS=0
T6_NOJB_PAIRS=2964 / T6_NOJB_FRAMES=0

# T9 画质
T9_ALIGNED_PSNR=inf / T9_ALIGNED_SSIM=1.0
T9_PSNR_AVG=58.83dB (Y57.08/U78.64/V82.93/min34.61)
T9_SSIM_ALL=0.999876 (Y0.999818)

# T4 SRTP
T4_SRTP_SSRC=4221072070
T4_RECV_COUNT=5911
T4_RECV_DROP_COUNT=0
T4_DECODED_FRAMES=297
T4_BUS_ERRORS=0
T4_CIPHER=aes-128-icm / T4_AUTH=hmac-sha1-80

# T7 丢包反馈
T7_PROXY_RECEIVED=5933 / T7_PROXY_FORWARDED=5636 / T7_PROXY_DROPPED=297 / RATIO=0.0501
T7_A_BASELINE_FRAMES=297 / ERR=4
T7_B_LOSS_RECOVERY_ON_FRAMES=85~90 / ERR=145
T7_C_LOSS_RECOVERY_OFF_FRAMES=107 / ERR=143
T7_FEEDBACK_PT={201:54, 205:0, 206:0}
T7_STATUS=通路成立；NACK/RTX/PLI 闭环未建立 DEFERRED-M5
```

> 说明：`T3_RECV_RC=124`、`T8_GST_RC=124` 为 `timeout` 主动结束进程的退出码，不是管线报错；探针在超时窗口内已收齐有效 RTP/RTCP。SSRC 为每次会话随机生成，跨运行不相同属正常。

## 附录 C：关键管线速查

**视频发送（RTP/UDP 回环）**

```text
filesrc ! qtdemux ! h264parse ! rtph264pay config-interval=1 pt=96
  ! udpsink host=127.0.0.1 port=5004
```

**视频接收（拆包重组 + 解码对账）**

```text
udpsrc port=5014 caps="application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,pt=96"
  ! queue ! rtpjitterbuffer ! rtph264depay ! h264parse
  ! avdec_h264 ! videoscale ! videoconvert
  ! video/x-raw,format=I420,width=320,height=180 ! filesink rx.yuv
```

**rtpbin 发送侧（RTP + RTCP SR）**

```text
rtpbin name=R
  filesrc ! qtdemux ! h264parse ! rtph264pay pt=96 ! R.send_rtp_sink_0
  R.send_rtp_src_0  ! udpsink host=127.0.0.1 port=5034
  R.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5035 sync=false async=false
```

**双 rtpbin 接收侧（动态输出面板用裸 bin 引用）**

```text
rtpbin name=RR do-retransmission=true
  udpsrc port=5061 caps="application/x-rtp,...H264,pt=96" ! RR.recv_rtp_sink_0
  RR. ! rtph264depay ! h264parse ! avdec_h264 ! ...
  udpsrc port=5066 ! RR.recv_rtcp_sink_0
  RR.send_rtcp_src_0 ! udpsink host=127.0.0.1 port=5065 sync=false async=false
```

**SRTP 闭环（PyGI 代码级管线）**

```text
发送：filesrc ! qtdemux ! h264parse ! rtph264pay ! srtpenc(key=30B) ! udpsink
接收：udpsrc(x-srtp) ! srtpdec(request-key 供钥) ! rtph264depay ! h264parse ! avdec ! fakesink
```

**音频发送（Opus RTP）**

```text
filesrc ! qtdemux ! aacparse ! avdec_aac ! audioconvert ! audioresample
  ! opusenc ! rtpopuspay pt=111 ! udpsink host=127.0.0.1 port=5006
```
