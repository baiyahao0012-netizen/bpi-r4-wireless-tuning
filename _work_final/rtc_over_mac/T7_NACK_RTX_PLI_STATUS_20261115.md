# T7 NACK / RTX / PLI 实测状态（2026-11-15）

> **更正（2026-11-15）**：本文的"计数器恒为 0"与"B≫C"两处结论已被 [MEDIA_BASELINE_V1_20261115.md](MEDIA_BASELINE_V1_20261115.md) 更正，详见该文档 §4、§5。

## 1. 结论

- **NACK → RTX 重传链路已在裸 `rtpsession` 实验台上验证打通**：RTX 包（PT 97）到达接收会话，jitterbuffer 用重传包成功恢复丢包；B 臂解码帧数显著高于 C 臂。
- **PLI（PT 206）出站尚未闭环**：Python 绑定的裸 `rtpsession` 没有暴露直接触发关键帧请求的 action signal；应用层手工注入 `GstForceKeyUnit` 上游事件被 pad 层拒绝，未观测到 PT 206 发出。
- T7 实验台脚本尚未提交仓库，避免半成品进入交接。

## 2. 实验口径

- 素材：Pi `/home/bai/rtc_test/clip10.mp4`。
- 本地回环：`--host 127.0.0.1`，RTP 5004，RTCP 5006，反馈 5005。
- 管线：文件 → H264 parse → pay(PT 96) → `rtprtxsend` → `rtpsession(avpf)`；接收侧 `rtpsession` → `rtprtxreceive` → `rtpssrcdemux` → `rtpjitterbuffer` → depay/parse/decoder。
- 证据口径：RTX 判定使用 **PT 97 包探针计数 + jitterbuffer `rtx-success-count`**；`rtprtxsend` / `rtprtxreceive` 的元件属性计数器在本实验中恒为 0，不作为 RTX 成功证据。

## 3. 三臂对照结果

| 臂 | 丢包 | RTX | 接收 net PT96 | 接收 net PT97 | 会话内 PT97 | jb 恢复成功 | jb 重复包 | 解码帧 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| B | 5% | 开 | 5,520 | 187 | 187 | 112 | 47 | 165 |
| C | 5% | 关 | 3,685 | 0 | 0 | 0 | 0 | 8 |

### B 臂明细（5% 丢包，RTX 开）

接收侧：

- `net_pt96=5520`，`net_pt97=187`，`in_pt97=187`。
- jitterbuffer：`num-pushed=5632`，`num-lost=302`，`num-duplicates=47`，`rtx-success-count=112`，`rtx-rtt≈37.9 ms`。
- 解码：165 帧。

发送侧：

- `out_pt96=5644`，`out_pt97=241`。
- 会话 `sent-rtx-req-count=406`，`in_NACK=2`。

### C 臂明细（5% 丢包，RTX 关）

- `net_pt96=3685`，`in_pt96=3685`，无 PT 97。
- jitterbuffer：`num-pushed=3685`，`num-lost=2248`，`rtx-success-count=0`。
- 解码：8 帧。

B 与 C 的差距证明 RTX 重传在该链路上有效。

## 4. A 臂无丢包基线

- 早期 A 臂：302/302 解码，5,933 个 RTP 包。
- 当前 15 秒脚本复跑：`net_pt96=5779`，解码 265 帧，jb `num-lost=155`。该尾部缺口来自固定停止时 jitterbuffer 未排空，不计为传输损失；冻结基线前需要复跑并确认尾部排空。

## 5. PLI 阻塞点

### 已核对源码与官方文档

- `gstrtpsession.c:1917-1930`：会话在 `recv_rtp_src` pad 拦截 `GstForceKeyUnit` 自定义上游事件，随后调用 `rtp_session_request_key_unit`。
- 仅当 caps 含 `rtcp-fb-nack-pli`（或 FIR 字段）时，会话才会生成 PLI/FIR。
- `rtpsession` Python introspection 只列出 `request-pt-map`、`clear-pt-map`、`on-new-ssrc` 等信号；**没有** `request-remote-key-unit` / `request-key-unit` action signal。
- 官方 rtpsession 文档同样只列出 `clear-pt-map` action signal，未提供应用层直接触发 PLI 的动作信号。

### 已尝试的注入路径

在 3 秒后构造 `GstForceKeyUnit`，字段含 `ssrc`、`payload=96`、`all-headers=false`，依次尝试以下 sink pad 注入上游事件：

1. 解码器 sink pad；
2. H264 parse sink pad；
3. depayloader sink pad；
4. jitterbuffer sink pad；
5. SSRC demux sink pad；
6. RTX receive sink pad。

结果：`force_key_unit_sent=0`，未观测到接收端 `out_PLI`，发送端未收到 PT 206。

### 判断

裸 `rtpsession` 实验台适合验证 NACK/RTX 事件接线；完整 PLI + 关键帧刷新闭环更适合在 `rtpbin` / `webrtcbin` 或实时编码器链路上验证：

- 标准 PLI 由下游解码侧在发现关键帧缺失时触发；
- 文件源不会按需生成新的 IDR；
- 即使 PLI RTCP 报文发出，文件发送侧也无法自然产出新的关键帧；
- 后续如需完整 PLI 往返，应使用实时编码器（如 `x264enc` / `vp8enc`）或标准 `webrtcbin` 链路，并在接收端观测 PT 206、发送端观测关键帧请求事件。

## 6. 未完成项

1. 复跑 A 臂，确认 jitterbuffer 尾部排空，得到稳定无丢包帧数基线。
2. PLI 标准往返：接收端 PT 206 出站 → 发送端收到 PT 206 → 发送编码器收到关键帧请求 → 关键帧恢复。
3. T8：双流、音频 jitterbuffer、SR NTP↔RTP 映射、跨机时钟 offset、A/V 同步锚点。

## 7. 相关文件

- 实验台：`tools/t7_rtx_lab.py`（未提交）。
- 本地源码：`gst-plugins-good-1.26.2/gst/rtpmanager/`。
- Pi 日志：`/tmp/t7_B2.log`、`/tmp/t7_C.log`、`/tmp/t7_A2.log`、`/tmp/t7_pli7.log`。
