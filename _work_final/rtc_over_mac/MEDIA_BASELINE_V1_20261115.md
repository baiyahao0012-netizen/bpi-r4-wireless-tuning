# 开源 RTC 媒体层基线 V1（视频路径）

日期：2026-11-15  
范围：**视频单流**，本地回环（Pi 上 sender / receiver 两进程），GStreamer 1.26.2  
定位：冻结"视频媒体路径 + 可复现实验口径"；T7 只冻结到"机制存在、验收未通过"，PLI 与 T8 归 v2。

---

## 1. 冻结结论（先看这段）

| 项 | 状态 | 证据 |
|---|---|---|
| T1 解码 / T2 RTP 头 / T5 RTCP SR / T6 乱序 / T9 画质 | ✅ 已通过 | L0 报告（字段级） |
| T3 严格 302/302 | ✅ 闭环 | `t3_eos_receiver.py` |
| T4 SRTP 302/302、0 drop | ✅ 闭环 | `srtp_loopback_eos.py` |
| **视频路径无丢包基线（A 臂）** | ✅ **302/302，3/3 复现** | 本文 §3 |
| **T7 NACK/RTX 机制** | 🟡 **存在但不可靠触发** | assoc>0 仅 4/15 次；见 §4 |
| **T7 帧级收益** | ❌ **未证明** | 5% 与 0.1% 丢包下 B≈C / D≈E |
| **T7 PLI(PT206)** | ❌ 未闭环 | 需实时编码器，v2 |
| **T8 音频/双流/A-V** | ❌ 未开始 | v2 |

**一句话**：视频路径可以冻结为 V1；T7 不能写成"通过"，只能写"机制已接线、验收未通过、根因已定位到 NACK 投递不可靠"。

---

## 2. 实验口径（冻结参数）

```
sender   filesrc -> qtdemux -> h264parse -> rtph264pay(pt=96)
         -> rtprtxsend(payload-type-map 96->97, max-size-packets=5000, max-size-time=5000)
         -> rtpsession(rtp-profile=3/AVPF, send_rtp_sink)
         -> identity(drop-probability=<p>) -> udpsink 127.0.0.1:5004
         rtpsession.send_rtcp_src -> udpsink 127.0.0.1:5006
         udpsrc 5005 -> queue -> rtpsession.recv_rtcp_sink

receiver udpsrc 5004 (H264 pt=96 caps, **buffer-size=8MB**)
         -> rtpsession(rtp-profile=3/AVPF)
         -> recv_rtp_src -> rtprtxreceive(96->97) -> rtpssrcdemux
         -> rtpjitterbuffer(latency=500, do-retransmission, rtx-delay=0, rtx-max-retries=8)
         -> rtph264depay -> h264parse -> avdec_h264 -> fakesink
         rtpsession.send_rtcp_src -> udpsink 5005
         udpsrc 5006 -> rtpsession.recv_rtcp_sink
```

关键约束（缺一条数值就不可信）：

1. **接收端 `udpsrc buffer-size=8MB`**。缺它时 A 臂只有 265/302（内核 socket 缓冲丢包），C 臂会被打到 3,685/5,647，制造出"RTX 很有效"的假象。
2. **RTX 计数器必须运行中采样**。`rtprtxsend` / `rtprtxreceive` 在 `PAUSED→READY` 清零（`gstrtprtxsend.c:1292`、`gstrtprtxreceive.c:1073`），管线 `set_state(NULL)` 之后再读恒为 0。
3. `rtp-profile` 必须是 3（AVPF）；枚举 1 是 AVP，不允许反馈。
4. 接收链必须有 `rtpssrcdemux`，否则 RTR 事件 SSRC 缺失，NACK 不调度。

---

## 3. A 臂：视频路径基线（冻结）

素材 `clip10.mp4`（10 s / 30 fps / 302 帧），丢包 0，RTX 开，3 次重复：

| rep | net_pt96 | 解码帧 | jb num-lost |
|---|---:|---:|---:|
| 1 | 5,933 | **302** | 1 |
| 2 | 5,933 | **302** | 1 |
| 3 | 5,933 | **302** | 1 |

**基线：302/302，3/3 复现，尾帧无滞留。** 这条可以冻结。

---

## 4. T7：机制存在，但验收未通过

### 4.1 5% 丢包（B = RTX 开，C = RTX 关）

| 臂 | 解码帧（3 次） | 中位数 | net_pt97 | assoc |
|---|---|---:|---:|---:|
| B | 136 / 140 / 140 | **140** | 184 / 1 / 1 | 184 / 0 / 0 |
| C | 138 / 138 / 138 | **138** | 0 | 0 |

**B ≈ C（+2 帧，0.7%）。** 5% 随机丢包下 RTX 没有帧级收益。

### 4.2 0.1% 丢包（D = RTX 开，E = RTX 关）

| 臂 | 解码帧（3 次） | 中位数 |
|---|---|---:|
| D | 294 / 298 / 294 | **294** |
| E | 294 / 294 / 294 | **294** |

**D ≈ E。** 0.1% 下同样没有可测收益；D2 是唯一一次 RTX 真正恢复（95 包关联、`rtx-success=4`、298 帧，比 E 多 4 帧）。

### 4.3 机制证据（不可否认的部分）

在 15 次运行中，有 4 次 `net_pt97 > 0` 且 `rtprtxreceive.num-rtx-assoc-packets > 0`：

| 运行 | PT97 到达 | assoc | rtx-success |
|---|---:|---:|---:|
| A2 | 82 | 82 | 0 |
| A3 | 63 | 63 | 0 |
| B1 | 184 | 184 | 63 |
| D2 | 95 | 95 | 4 |

`assoc > 0` 说明重传流能被正确关联——**RTX 机制本身是通的**，问题在触发率。

### 4.4 根因（已定位，未修复）

- 接收端会话日志 `sent-nack-count = 145 ~ 1,306`，但 RTCP 出站探针 `out_NACK` 只有 4–6 个包，发送端 `in_NACK` 只有 1–2 个。
- 即 **NACK 调度起来了，但真正发出去的反馈包很少，且大部分没到发送端**；发送端 `out_pt97` 因此多数时候只有 1（等于没有重传）。
- 待查方向：RTCP 反馈的发送间隔/聚合、`rtpssrcdemux` 之后的 SSRC 与 `rtprtxsend` 历史键是否一致、`rtx-delay=0` 是否导致 NACK 集中在会话边界发出。

**结论：T7 不能判"通过"。** 上一份交接里的"B=165 vs C=8 证明 RTX 有效"是接收端缓冲缺口的假象（C 臂被缓冲丢包打到 3,685 包），补上 8 MB 后 C 恢复到 138 帧，差距消失。

### 4.5 参数扫描（2026-11-15 追加）：RTX 为什么"没效果"

按 GStreamer 官方示例（`tests/examples/rtp/{server,client}-rtpaux.c`）和 `rtpsession.c` 源码复核后，确认两条约束：

1. **RTX 参数必须留默认（-1 自动）**。硬设 `rtx-delay=0 / rtx-max-retries=8` 会关掉基于 RTT 的自动调度。
2. **NACK 能否发出取决于它能否活过一个 RTCP 周期**。`rtpsession.c:4930` 的 `T_rr` 取 RFC 3550 带宽公式算出的周期（约 1 s），而 jitterbuffer 默认只给 ~120 ms 的 `max_delay`；`rtp_session_request_nack` 的早发失败后，NACK 会在下一个 RTCP 周期前过期（`session_nack` 里清理 deadline 过期的请求）。

由此做 4×3 扫描（5% 丢包，`rtcp-min-interval=100ms`，`rtx-retry-timeout=200ms`）：

| 抖动缓冲 | p300 | p600 | p1000 |
|---|---:|---:|---:|
| 500 ms | 144 | **179** | 148 |
| 800 ms | 155 | 140⚠ | 144 |
| 1200 ms | 140⚠ | 142 | 141 |
| 1500 ms | 161 | 140⚠ | 148 |

无 RTX 的 C 臂在四个延迟下恒为 **138**（延迟本身救不回丢包）。⚠ 表示该次完全没有 RTX 包（`net_pt97=1`），同时伴随 **RTCP 风暴**（`out_RR` 700–1000、`out_NACK` 600+）。

**最好点（500 ms + p600）重复 5 次**：149 / 140 / 152 / 140 / 138，中位数 **140**——与无 RTX 的 138 无实质差别；179 是离群值。5 次中有 1 次进入 RTCP 风暴且 RTX 全灭。

### 4.6 对 T7 的最终判定

| 结论 | 证据 |
|---|---|
| RTX **机制**可用 | 运行中 `rtprtxreceive.num-rtx-assoc-packets` 最高 131、`rtx-success-count` 最高 66、PT97 到达与关联一致 |
| RTX **帧级收益**不成立 | 5% 随机丢包下，500–1500 ms 延迟、300–1000 ms 重传窗口，中位数均为 140 vs C 臂 138 |
| 存在**反馈风暴**失效模式 | `out_RR` 700–1000 时 RTX 全灭，需要限速 NACK（`rtx-max-retries` 或发送端 RTCP 预算） |

原因：1080p、约 14 包/帧，5% 随机丢包下每帧至少丢 1 包的概率约 50%；RTX 只能追回其中一部分，参考链仍然断裂，帧数几乎不变。**要让 T7 有可验收的帧级收益，应改用能全部追回的丢包模型（突发丢包 + 足够窗口），或在实时编码器链路上做 PLI 刷新。**

---

## 5. 与旧交接的差异（更正清单）

| 旧结论 | 更正 |
|---|---|
| `rtprtxsend/receive` 计数器"恒为 0、不能作证据" | **错**。是读完时机问题；运行中采样非零（见 §4.3） |
| A 臂 265/302 是"停止窗口尾部未排空" | **错**。是接收端 socket 缓冲丢包；补 8 MB 后 302/302 |
| B=165 vs C=8 证明 RTX 有效 | **不成立**。C 臂被缓冲丢包污染；修复后 B≈C |
| PLI 手工注入失败 → 会话不能发 PLI | 只证明"事件没送达会话"，未证明会话拒绝；完整 PLI 需实时编码器 |

---

## 6. V1 冻结范围与遗留

**冻结**：

- 视频媒体路径（T1、T2、T5、T6、T9）；
- 严格帧数闭环脚本（T3、T4）；
- A 臂 302/302 基线；
- 本实验口径（8 MB 缓冲、运行中采样、AVPF、ssrcdemux）。

**不冻结、归 v2**：

1. T7 的 NACK 投递可靠性（唯一阻塞 T7 验收的问题）；
2. PLI(PT206) 往返 + 关键帧刷新（需 `x264enc` 实时链路）；
3. T8：双流、音频 jb、RTCP SR NTP↔RTP、跨机时钟、A/V 锚点；
4. 真实链路（非回环）上的 T7/T8 复测。

---

## 7. 复现命令

```bash
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
# A/B/C 三臂 x3（5% 丢包）
bash tools/run_t7_matrix.sh
# D/E 两臂 x3（0.1% 丢包）
bash tools/run_t7_lowloss.sh
# 单跑
python3 tools/t7_rtx_lab.py receiver --seconds 16 --latency 500
python3 tools/t7_rtx_lab.py sender --file /home/bai/rtc_test/clip10.mp4 --seconds 11
```

数据：`t7_v1_matrix_20261115.csv`、`t7_sweep_20261115.csv`；脚本：`tools/t7_rtx_lab.py`、`tools/run_t7_matrix.sh`、`tools/run_t7_lowloss.sh`、`tools/run_t7_sweep.sh`、`tools/rtp_media_lab.py`（rtpbin 版，已按官方 aux 示例对齐）。
