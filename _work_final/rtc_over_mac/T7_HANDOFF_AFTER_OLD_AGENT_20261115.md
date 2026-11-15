# T7 后续进展交接文档（旧 Agent 停止后）

> **更正（2026-11-15）**：本文两处结论已被 [MEDIA_BASELINE_V1_20261115.md](MEDIA_BASELINE_V1_20261115.md) 更正：
> ① `rtprtxsend/receive` 的 `num-rtx-*` **并非"恒为 0"**，而是元件在 `PAUSED→READY` 时清零（`gstrtprtxsend.c:1292`、`gstrtprtxreceive.c:1073`），`set_state(NULL)` 之后再读才为 0；运行中采样非零（assoc 最高 184）。
> ② **"B=165 vs C=8" 不成立**：C 臂被接收端缺失 `buffer-size=8MB` 的 socket 丢包污染；补上后 C=138，B≈C（140），RTX 无帧级收益。

> 用途：把上一个 Agent 停在“RTX 未建立、怀疑 send-only 会话不激活 RTCP 接收腿”之后，本轮已经完成的排查、代码改动、实测证据、源码依据和剩余阻塞点完整交接。接手 Agent 阅读本文即可恢复上下文，不需要回看旧日志轨迹。

## 1. 一句话现状

- **NACK → RTX 重传链路已在裸 `rtpsession` 实验台上验证打通**：RTX 包（PT 97）到达接收会话，jitterbuffer 用重传包成功恢复丢包；B 臂 165 帧，C 臂无 RTX 仅 8 帧。
- **PLI（RTCP PT 206）出站尚未闭环**：裸 `rtpsession` Python 绑定没有直接触发关键帧请求的 action signal；应用层手工注入 `GstForceKeyUnit` 上游事件被 pad 层拒绝，未观测到 PT 206。
- T7 实验台脚本目前**只在本地和 Pi `/tmp`，未提交仓库**。远程仓库里仍是旧的 L2 结果提交 `2f08e38`、`c2503cd`，没有被半成品污染。

## 2. 旧 Agent 卡点与本轮修正后的判断

### 2.1 旧 Agent 当时看到的证据

旧版本脚本中：

| 计数器 | 当时值 | 当时判断 |
|---|---:|---|
| 接收侧 `out_NACK` | 8 | 接收端在发 NACK |
| jitterbuffer `rtx-count` | 1,900+ | 仅跟踪重传事件，不是 RTX 成功证据 |
| `rtprtxreceive.num-rtx-assoc-packets` | 0 | 未关联重传流 |
| 发送侧 `rtprtxsend.num-rtx-requests` | 0 | 未收到重传请求 |
| 发送侧 `rtprtxsend.num-rtx-packets` | 0 | 未重发 |

旧 Agent 进一步怀疑：发送端“只发不收”，所以 `recv_rtcp_sink` 未激活，`udpsrc 5005` 被 not-linked 后停止。

### 2.2 本轮最新结果：该假设已被 supersede

当前脚本的发送端 RESULT 显示：

- `rtcp_src_link_ret = "ok"`
- `rtcp_src_src_linked = 1`
- `fb_linked = 1`
- `rtcp_in_raw > 0`
- 发送端能看到 `in_RR`、`in_NACK`

也就是说，**当前版本下发送端 RTCP 反馈腿已经绑定、链接并收到 RTCP 报文**。旧日志里“udpsrc 被 stop called / socket 关闭”是早期脚本版本的症状；在当前脚本上不应继续优先追这个方向。

### 2.3 真正定位到的三个根因

#### 根因 A：接收链缺少 `rtpssrcdemux`，RTR 事件 SSRC 为 `FFFFFFFF`

jitterbuffer 生成的 `GstRTPRetransmissionRequest`（RTR）事件结构本身不带 `ssrc`。裸接收链最初是：

```text
udpsrc -> rtpsession.recv_rtp_sink -> rtprtxreceive -> rtpjitterbuffer
```

缺少 SSRC demux 时，上游 RTR 事件回到 `rtpsession` 后，结构里没有 `ssrc`；会话 `find_source(sess, ssrc)` 返回 NULL，NACK 调度被放弃。调试日志里事件 SSRC 显示为 `FFFFFFFF` / 未知。

源码依据：

- `gstrtpjitterbuffer.c:4338-4348`：jb 创建 `GstRTPRetransmissionRequest`，结构含 `seqnum/running-time/delay/retry/...`，但没有 SSRC 字段。
- `gstrtpssrcdemux.c:867-881`：demux 发现自定义上游事件结构没有 `ssrc` 时，用本 demux pad 对应的 SSRC 补上 `"ssrc"`。
- `gstrtpssession.c:1931-1961`：会话收到 RTR 后读 `ssrc`，缺省为 `-1`，再调 `rtp_session_request_nack(...)`。

当前接收链已改为：

```text
rtpsession.recv_rtp_src -> rtprtxreceive -> rtpssrcdemux -> rtpjitterbuffer
```

demux 的 src pad 按 SSRC 动态生成；信号回调签名是 `(demux, ssrc, pad)`。

#### 根因 B：RTX 历史缓冲默认只留 100 包，NACK 到达时原始包已淘汰

`rtprtxsend` 默认历史缓冲 `max-size-packets=100`、`max-size-time=0`。突发 RTP 流中，NACK 到达时目标原始包多数已从 RTX buffer 淘汰。当前脚本把发送端 RTX 历史扩容：

```python
rtx.set_property("max-size-packets", 5000)
rtx.set_property("max-size-time", 5000)  # ms
```

修复后 24_2 对照片段中 PT 97 到达从个位数升到 187 个；完整 33 秒 PLI 探针日志中甚至出现 `net_pt97=538`、`in_pt97=537`。

#### 根因 C：RTP profile 必须是 AVPF（枚举 3），不是 AVP（枚举 1）

实测 `GstRTPProfile`：

| 枚举 | profile |
|---:|---|
| 0 | unknown |
| 1 | avp |
| 2 | savp |
| 3 | avpf |
| 4 | savpf |

旧脚本误写 `rtp-profile=1`（AVP）。AVP 不允许反馈报文；当前脚本两端均设为 3（AVPF）。

### 2.4 配套修复

1. **接收端 `request-pt-map` 返回带反馈能力的 H264 caps**：

   ```text
   application/x-rtp,media=video,encoding-name=H264,clock-rate=90000,
   rtcp-fb-nack=(boolean)true,rtcp-fb-nack-pli=(boolean)true
   ```

2. **接收端 `udpsrc` caps 回滚为显式 H264 PT 96**：

   ```text
   application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000
   ```

   不要把 caps 放宽成通用 `application/x-rtp,media=video,...`；旧版本因此出现 depay `not-negotiated(-4)`，接收 3 包后报错。RTX PT 97 由会话 / RTX 元件按 SSRC 识别，不需要在 `udpsrc` caps 里列 PT 97。

3. **增加三位置 PT 探针**：
   - 发送端 `drop.src`：`out_pt96/out_pt97`；
   - 接收端 `udpsrc.src`：`net_pt96/net_pt97`；
   - 接收端会话 `recv_rtp_src`：`in_pt96/in_pt97`。
   - 同时记录首个 RTP SSRC。

## 3. 实验环境与复现命令

### 3.1 环境

- Pi：`bai@192.168.240.153`，Debian 13 aarch64，GStreamer 1.26.2。
- 本地回环：`--host 127.0.0.1`。
- 端口：RTP 5004，RTCP 5006，反馈 RTCP 5005。
- 素材：`/home/bai/rtc_test/clip10.mp4`。
- 运行前必须设置 GI typelib 路径：

  ```bash
  export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
  ```

### 3.2 当前脚本位置

| 位置 | 文件 | SHA256 |
|---|---|---|
| Windows 本地 | `D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\tools\t7_rtx_lab.py` | `ae08e5414997ac0bfe8b1cd52eadad381630e85fa6c521e004bfea8c3b4cb9f4` |
| Pi `/tmp` | `/tmp/t7_rtx_lab.py` | 同上，已核对一致 |
| Windows 本地 | `D:\Desktop\AI 辅助对话\_work_final\rtc_over_mac\tools\run_t7.sh` | `ed7b5ad2e67f4fd87b9ed2f91dd13054e4d31cae0b90886b9b909c80ab3b805b` |
| Pi `/tmp` | `/tmp/run_t7.sh` | 同上，已核对一致 |
| Windows 本地 | `tools\inspect_rtpsession.py` | 信号 introspection 诊断脚本 |

### 3.3 Runner

```bash
bash /tmp/run_t7.sh 0.0 15         # A 臂：无丢包，RTX 开
bash /tmp/run_t7.sh 0.05 15        # B 臂：5% 丢包，RTX 开
bash /tmp/run_t7.sh 0.05 15 no-rtx # C 臂：5% 丢包，RTX 关
```

Runner 先起 receiver，2 秒后起 sender；两端日志分别落 `/tmp/recv_t7.log`、`/tmp/send_t7.log`，最后 `cat` 到终端。

直接角色命令口径：

```bash
python3 /tmp/t7_rtx_lab.py receiver --file /home/bai/rtc_test/clip10.mp4 \
  --host 127.0.0.1 --rtp-port 5004 --rtcp-port 5006 --feedback-port 5005 \
  --loss 0.0 --latency 500 --seconds 15

python3 /tmp/t7_rtx_lab.py sender --file /home/bai/rtc_test/clip10.mp4 \
  --host 127.0.0.1 --rtp-port 5004 --rtcp-port 5006 --feedback-port 5005 \
  --loss 0.05 --latency 500 --seconds 15
```

## 4. 实测结果（证据口径）

### 4.1 关键计数口径（避免误判）

在 GStreamer 1.26.2 本次实验中，以下元件属性读数始终为 0，**不能作为 RTX 成功证据**：

- `rtprtxsend.num-rtx-requests`
- `rtprtxsend.num-rtx-packets`
- `rtprtxreceive.num-rtx-assoc-packets`

判定 RTX 成功必须使用：

1. 网络探针 `net_pt97 > 0`；
2. 会话内探针 `in_pt97 > 0`；
3. jitterbuffer `rtx-success-count > 0`；
4. 辅助参考：`rtx-per-packet`、`rtx-rtt`。

### 4.2 B 臂：5% 丢包，RTX 开

接收端 RESULT：

```json
{
  "role": "receiver", "loss": 0.0, "no_rtx": false,
  "stats": {
    "net_pt96": 5520, "out_RR": 7, "out_202": 7, "in_pt96": 5520,
    "out_NACK": 4, "net_pt97": 187, "in_pt97": 187,
    "rtcp_in_raw": 1, "decoded_frames": 165
  },
  "rtxrecv": {"requests": 0, "packets": 0, "assoc": 0},
  "jitterbuffer": {
    "num-pushed": 5632, "num-lost": 302, "num-late": 0,
    "num-duplicates": 47, "avg-jitter": 6847795,
    "rtx-count": 2012, "rtx-success-count": 112,
    "rtx-per-packet": 1.0001655787654415, "rtx-rtt": 37897816,
    "rfc7273-active": false
  },
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 2012, "recv-rtx-req-count": 2012, "sent-rtx-req-count": 0
  }
}
```

发送端 RESULT：

```json
{
  "role": "sender", "loss": 0.05, "no_rtx": false,
  "stats": {
    "rtcp_src_link_ret": "ok", "rtcp_src_port": 5005,
    "rtcp_src_src_linked": 1, "fb_linked": 1,
    "rtp_sent": 5885, "out_pt96": 5644,
    "rtcp_in_raw": 3, "in_RR": 3, "in_202": 3, "in_NACK": 2,
    "out_pt97": 241, "out_SR": 1, "out_202": 1, "out_203": 1
  },
  "rtxsend": {"requests": 0, "packets": 0},
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 0, "recv-rtx-req-count": 0, "sent-rtx-req-count": 406
  }
}
```

B 臂要点：

- PT 97 网络到达 187，进入会话 187；
- jitterbuffer 成功恢复 112 次；
- RTX RTT 约 `37.897816 ms`；
- 解码 165 帧。

### 4.3 C 臂：5% 丢包，RTX 关

接收端 RESULT：

```json
{
  "role": "receiver", "loss": 0.0, "no_rtx": true,
  "stats": {
    "net_pt96": 3685, "in_pt96": 3685,
    "out_RR": 4, "out_202": 4, "rtcp_in_raw": 1,
    "decoded_frames": 8
  },
  "rtxrecv": {"requests": 0, "packets": 0, "assoc": 0},
  "jitterbuffer": {
    "num-pushed": 3685, "num-lost": 2248, "num-late": 0,
    "num-duplicates": 0, "avg-jitter": 9961279,
    "rtx-count": 0, "rtx-success-count": 0,
    "rtx-per-packet": 0.0, "rtx-rtt": 0, "rfc7273-active": false
  },
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 0, "recv-rtx-req-count": 0, "sent-rtx-req-count": 0
  }
}
```

发送端 RESULT：

```json
{
  "role": "sender", "loss": 0.05, "no_rtx": false,
  "stats": {
    "rtcp_src_link_ret": "ok", "rtcp_src_port": 5005,
    "rtcp_src_src_linked": 1, "fb_linked": 1,
    "rtp_sent": 5647, "out_pt96": 5647,
    "rtcp_in_raw": 1, "in_RR": 1, "in_202": 1,
    "out_SR": 1, "out_202": 1, "out_203": 1
  },
  "rtxsend": {"requests": 0, "packets": 0},
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 0, "recv-rtx-req-count": 0, "sent-rtx-req-count": 0
  }
}
```

C 臂要点：

- 无 PT 97；
- jitterbuffer `rtx-success-count=0`；
- 解码仅 8 帧。

B/C 对照成立：RTX 对 H.264 参考链丢包恢复有明显增益。

### 4.4 A 臂：无丢包基线（15 秒脚本复跑）

接收端 RESULT：

```json
{
  "role": "receiver", "loss": 0.0, "no_rtx": false,
  "stats": {
    "net_pt96": 5779, "in_pt96": 5779, "out_RR": 11, "out_202": 11,
    "out_NACK": 8, "net_pt97": 1, "rtcp_in_raw": 1,
    "decoded_frames": 265
  },
  "rtxrecv": {"requests": 0, "packets": 0, "assoc": 0},
  "jitterbuffer": {
    "num-pushed": 5779, "num-lost": 155, "num-late": 0,
    "num-duplicates": 0, "avg-jitter": 6532094,
    "rtx-count": 1093, "rtx-success-count": 0,
    "rtx-per-packet": 0.0, "rtx-rtt": 0, "rfc7273-active": false
  },
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 1093, "recv-rtx-req-count": 1093, "sent-rtx-req-count": 0
  }
}
```

发送端 RESULT：

```json
{
  "role": "sender", "loss": 0.0, "no_rtx": false,
  "stats": {
    "rtcp_src_link_ret": "ok", "rtcp_src_port": 5005,
    "rtcp_src_src_linked": 1, "fb_linked": 1,
    "rtp_sent": 5934, "out_pt96": 5933,
    "rtcp_in_raw": 2, "in_RR": 2, "in_202": 2, "in_NACK": 1,
    "out_pt97": 1, "out_SR": 1, "out_202": 1, "out_203": 1
  },
  "rtxsend": {"requests": 0, "packets": 0},
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 0, "recv-rtx-req-count": 0, "sent-rtx-req-count": 1
  }
}
```

注意：A 臂当前 15 秒停止口径下 jb `num-lost=155`，这是固定停止时 jitterbuffer 尾部未排空导致，不是传输损失。冻结基线前需要复跑并确认尾部排空；早期 L0 本地回环曾得到 302/302、5933 包。

### 4.5 PLI 探针日志（`/tmp/t7_pli7.log`）

接收端：

```json
{
  "role": "receiver", "loss": 0.0, "no_rtx": false,
  "stats": {
    "net_pt96": 4237, "ssrc": 2379101488, "out_RR": 8, "out_202": 8,
    "in_pt96": 4237, "out_NACK": 6, "net_pt97": 538, "in_pt97": 537,
    "rtcp_in_raw": 3, "decoded_frames": 108, "force_key_unit_sent": 0
  },
  "rtxrecv": {"requests": 0, "packets": 0, "assoc": 0},
  "jitterbuffer": {
    "num-pushed": 4685, "num-lost": 1231, "num-late": 0,
    "num-duplicates": 22, "avg-jitter": 2715037,
    "rtx-count": 8460, "rtx-success-count": 448,
    "rtx-per-packet": 1.9596664574105511, "rtx-rtt": 91115932,
    "rfc7273-active": false
  },
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 8460, "recv-rtx-req-count": 8460, "sent-rtx-req-count": 0
  }
}
```

发送端：

```json
{
  "role": "sender", "loss": 0.0, "no_rtx": false,
  "stats": {
    "rtcp_src_link_ret": "ok", "rtcp_src_port": 5005,
    "rtcp_src_src_linked": 1, "fb_linked": 1,
    "rtp_sent": 6816, "out_pt96": 5933, "ssrc": 2379101488,
    "rtcp_in_raw": 3, "in_RR": 3, "in_202": 3, "in_NACK": 2,
    "out_pt97": 883, "out_SR": 3, "out_202": 3, "out_203": 1
  },
  "rtxsend": {"requests": 0, "packets": 0},
  "session": {
    "rtx-drop-count": 0, "sent-nack-count": 0, "recv-nack-count": 0,
    "rtx-count": 0, "recv-rtx-req-count": 0, "sent-rtx-req-count": 1148
  }
}
```

这条日志里 RTX 仍然工作（`rtx-success-count=448`），但 `force_key_unit_sent=0`，两侧都没有 PT 206 / PLI 计数。

## 5. PLI 阻塞点细节

### 5.1 源码链路

1. 标准链路中，下游解码侧产生上游 `GstForceKeyUnit` 自定义事件。
2. `gstrtpssession.c:1917-1930` 在 `recv_rtp_src` pad 拦截 `GstForceKeyUnit`：
   - 结构必须有 `ssrc`、`payload`；
   - 可选 `all-headers`、`count`；
   - 满足条件后调用 `gst_rtp_session_request_remote_key_unit(...)`。
3. 会话仅在 PT caps 含 `rtcp-fb-nack-pli`（或 FIR 字段）时，才调用内部 `rtp_session_request_key_unit`。
4. `rtpsession.c:4017-4039` 的 `session_pli(...)` 构造 PSFB PLI：
   - `GST_RTCP_TYPE_PSFB`；
   - `GST_RTCP_PSFB_TYPE_PLI`；
   - 设置 sender SSRC 和 media SSRC；
   - `source->send_pli` 置 FALSE。

### 5.2 introspection 与官方文档结论

在 Pi 上用 PyGI introspection 列出裸 `rtpsession` 信号：只有 `request-pt-map`、`clear-pt-map`、`on-new-ssrc`、`on-new-sender-ssrc` 等，**没有**直接触发 PLI / FIR / keyunit 的 action signal。

官方 `rtpsession` 文档的 Action Signals 也只列 `clear-pt-map`；官方 keyframe 文档描述的是“下游元件发送 upstream `GstForceKeyUnit`，编码器消费事件并产生新关键帧”，并没有提供应用层直接让会话发 PLI 的 action API。

### 5.3 已尝试的事件注入路径

3 秒后构造事件：

```python
st = Gst.Structure.new_empty("GstForceKeyUnit")
v = GObject.Value()
v.init(GObject.TYPE_UINT)
v.set_uint(ssrc)
st.set_value("ssrc", v)

v2 = GObject.Value()
v2.init(GObject.TYPE_UINT)
v2.set_uint(96)
st.set_value("payload", v2)

v3 = GObject.Value()
v3.init(GObject.TYPE_BOOLEAN)
v3.set_boolean(False)
st.set_value("all-headers", v3)

ev = Gst.Event.new_custom(Gst.EventType.CUSTOM_UPSTREAM, st.copy())
```

候选 sink pad 顺序：

1. `dec.sink`
2. `parse.sink`
3. `depay.sink`
4. `jb.sink`
5. `demux.sink`
6. `rtx.sink`

结果：所有 pad 的 `push_event(...)` 未使 `force_key_unit_sent` 变 1；日志未出现 PT 206。

### 5.4 当前判断

- 裸 `rtpsession` + Python 实验台适合验证 NACK/RTX 事件接线；**完整 PLI + 关键帧刷新闭环不应继续死磕这条手工事件注入路径**。
- 文件源不会按需生成新 IDR；即使 PLI RTCP 报文发出，文件发送侧也无法自然产出新关键帧。
- 建议把 PLI 验证移到以下任一标准链路上：
  - `rtpbin` + 标准 aux/jb 接线；
  - `webrtcbin`；
  - 实时编码器（如 `x264enc` / `vp8enc`）配合解码器缺关键帧触发路径。
- 验收 PLI 时应分别观测：
  1. 接收侧 RTCP 出站出现 PT 206；
  2. 发送侧 RTCP 入站收到 PT 206；
  3. 发送编码器收到关键帧请求；
  4. 发送侧产生新 IDR / 关键帧恢复。

## 6. 管线现状

### 6.1 发送端

```text
filesrc -> qtdemux -> h264parse -> rtph264pay(PT96)
  -> rtprtxsend(96->97, RTX buffer 5000 packets / 5000 ms)
  -> rtpsession(AVPF, send_rtp_sink)
  -> identity(drop-probability) -> udpsink 127.0.0.1:5004

rtpsession.send_rtcp_src -> udpsink 127.0.0.1:5006
udpsrc 5005 -> queue -> rtpsession.recv_rtcp_sink
```

### 6.2 接收端

```text
udpsrc 5004 (H264 PT96 caps) -> rtpsession.recv_rtp_sink
rtpsession.recv_rtp_src -> rtprtxreceive(96->97)
  -> rtpssrcdemux -> rtpjitterbuffer(do-retransmission, latency=500 ms)
  -> rtph264depay -> h264parse -> avdec_h264 -> fakesink

rtpsession.send_rtcp_src -> udpsink 127.0.0.1:5005
udpsrc 5006 -> rtpsession.recv_rtcp_sink
```

## 7. 已排除的死路（不要重复排查）

| 假设 | 排除依据 |
|---|---|
| link 失败 | `link_ret=ok`，两端 `is_linked=1` |
| 端口冲突 | 5005 / 6005 均试过，无冲突 |
| 接线顺序问题 | 当前脚本先接 RTCP 反馈腿再接 RTP 侧，问题不再复现 |
| 下游 pad 未激活 | 加 `queue` 缓冲无效；最终根因不是此点 |
| 元件缺失 | 接收端同代码能正常收到 SR / RR |
| `rtprtxreceive` 阻断上游事件 | `--no-rtxrecv` 旁路实验后 NACK 仍为 0，排除 |
| 裸会话缺 demux 后 ssrc 问题 | 已确认：补 demux 后 PT 97 可到达，RTX 成功计数大于 0 |
| RTX 属性计数器可读作成功证据 | 1.26.2 构建中这些属性恒为 0，已改用 PT 探针 + jb 统计 |

## 7.1 `rtpbin` 版实验台同步修正

`tools/rtp_media_lab.py` 是另一条标准 `rtpbin` 参考路径，已同步修正两个旧问题：

1. `rtp-profile` 同样从误写的 AVP(1) 改为 AVPF(3)。
2. `rtprtxsend` / `rtprtxreceive` 由 `request-aux-sender` / `request-aux-receiver` 信号回调返回；回调中负责把 aux 元件交给 rtpbin，**不能在主线程提前 `p.add(...)`**。
3. 自定义 jitterbuffer 由 `request-jitterbuffer` 信号回调创建并返回；同样不能提前加入管线。

该脚本用于后续 PLI / 标准 Bin 链路复现；当前三臂结果以裸 `rtpsession` 版 `t7_rtx_lab.py` 为准。

## 8. 尚未完成的事项

### T7 剩余

1. A 臂尾部 jitterbuffer 排空复核，得到稳定无丢包帧数基线。
2. PLI 标准往返：PT 206 出站 → 发送侧收到 → 编码器关键帧请求 → 新 IDR / 关键帧恢复。
3. T7 代码三臂稳定后再提交仓库。

### T8（尚未开始）

- 双流（视频 + 音频）；
- 音频 jitterbuffer；
- RTCP SR 的 NTP ↔ RTP 时间戳映射；
- 跨机时钟 offset 校正；
- A/V 同步锚点与偏差测量。

### 项目路线提醒

主线顺序仍应是：

1. 开源 RTC 媒体层跑通并冻结 UDP/IP 基线；
2. 再去 UDP/IP，改 L2 shim；
3. 最终形态 B：RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC。

L2 原型已有六片矩阵结果，但不要在媒体层基线冻结前回到第二步。

## 9. 建议接手顺序

1. **先复跑当前 A/B/C**：确认 B `net_pt97=187`、`rtx-success-count=112`；C `rtx-success-count=0`、解码 8 帧；A 尾部缺口仅来自 jb 未排空。
2. **决定 PLI 验证载体**：裸 `rtpsession` 手工事件注入已证明不可行；建议切到 `rtpbin` / `webrtcbin` 或实时编码器链路，不要在当前脚本继续换 pad 推事件。
3. **T7 收口后再进 T8**：先把双流、音频 jb、SR 时间映射和时钟 offset 闭环。
4. **冻结媒体层基线后再动 L2 shim**。

## 10. 附录：核心脚本

### 10.1 `tools/t7_rtx_lab.py`

```python
#!/usr/bin/env python3
"""T7 lab: NACK / RTX / PLI over rtpsession (the official GStreamer combination).

sender   file -> h264parse -> rtph264pay(96) -> rtprtxsend -> rtpsession(avpf)
         rtpsession.send_rtp_src -> [identity drop-probability] -> udpsink 5004
         rtpsession.send_rtcp_src -> udpsink 5006
         udpsrc 5005 -> rtpsession.recv_rtcp_sink

receiver udpsrc 5004 -> rtpsession(avpf)
         rtpsession.recv_rtp_src -> rtprtxreceive -> rtpssrcdemux -> rtpjitterbuffer
（rtpssrcdemux 给 RTR 上游事件补 ssrc；缺它会话 find_source 失败，NACK 不调度）
         jitterbuffer(do-retransmission) -> rtph264depay -> h264parse -> avdec_h264
         rtpsession.send_rtcp_src -> udpsink 5005
         udpsrc 5006 -> rtpsession.recv_rtcp_sink
"""
import argparse
import json
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib, GObject  # noqa: E402

Gst.init(None)

PT_NAMES = {200: "SR", 201: "RR", 205: "NACK", 206: "PLI"}
HOLDER = {}


def make(factory, name):
    el = Gst.ElementFactory.make(factory, name)
    if el is None:
        raise RuntimeError("missing element: %s" % factory)
    return el


def pt_map_structure():
    res = Gst.Structure.from_string("application/x-rtp-pt-map,96=(uint)97")
    for item in res:
        if isinstance(item, Gst.Structure):
            return item
    raise RuntimeError("bad pt map")


def probe_buffer(info):
    for name in ("get_buffer", "get_current_buffer"):
        fn = getattr(info, name, None)
        if fn is not None:
            try:
                b = fn()
                if b is not None:
                    return b
            except Exception:
                pass
    try:
        if isinstance(info.data, Gst.Buffer):
            return info.data
    except Exception:
        pass
    return None


def rtcp_pts(buf):
    out = []
    try:
        data = bytes(buf.extract_dup(0, buf.get_size()))
    except Exception:
        return out
    i = 0
    while i + 4 <= len(data):
        if (data[i] >> 6) != 2:
            break
        pt = data[i + 1]
        ln = ((data[i + 2] << 8) | data[i + 3]) * 4 + 4
        out.append(pt)
        if ln <= 0:
            break
        i += ln
    return out


def rtp_pt(buf):
    try:
        data = bytes(buf.extract_dup(0, buf.get_size()))
    except Exception:
        return None
    if len(data) >= 2 and (data[0] >> 6) == 2:
        return data[1] & 0x7f
    return None


def probe_rtp_pt(pad, stats, tag):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            pt = rtp_pt(buf)
            if pt is not None:
                k = "%s_pt%d" % (tag, pt)
                stats[k] = stats.get(k, 0) + 1
                try:
                    data = bytes(buf.extract_dup(0, buf.get_size()))
                    if len(data) >= 12 and "ssrc" not in stats:
                        stats["ssrc"] = int.from_bytes(data[8:12], "big")
                except Exception:
                    pass
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_rtcp(pad, stats, tag):
    def cb(p, info):
        buf = probe_buffer(info)
        if buf is not None:
            for pt in rtcp_pts(buf):
                k = "%s_%s" % (tag, PT_NAMES.get(pt, str(pt)))
                stats[k] = stats.get(k, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def probe_count(pad, stats, key):
    def cb(p, info):
        stats[key] = stats.get(key, 0) + 1
        return Gst.PadProbeReturn.OK
    pad.add_probe(Gst.PadProbeType.BUFFER, cb)


def build_sender(a, stats):
    p = Gst.Pipeline.new("sender")
    src = make("filesrc", "src")
    src.set_property("location", a.file)
    demux = make("qtdemux", "demux")
    parse = make("h264parse", "parse")
    pay = make("rtph264pay", "pay")
    pay.set_property("pt", 96)
    pay.set_property("config-interval", 1)
    rtx = make("rtprtxsend", "rtxsend")
    rtx.set_property("payload-type-map", pt_map_structure())
    rtx.set_property("max-size-packets", 5000)
    rtx.set_property("max-size-time", 5000)
    sess = make("rtpsession", "sess")
    sess.set_property("rtp-profile", 3)  # AVPF（枚举：1=avp, 3=avpf）
    drop = make("identity", "drop")
    drop.set_property("drop-probability", a.loss)
    rtp_sink = make("udpsink", "rtp_sink")
    rtp_sink.set_property("host", a.host)
    rtp_sink.set_property("port", a.rtp_port)
    rtp_sink.set_property("sync", False)
    rtp_sink.set_property("async", False)
    rtcp_sink = make("udpsink", "rtcp_sink")
    rtcp_sink.set_property("host", a.host)
    rtcp_sink.set_property("port", a.rtcp_port)
    rtcp_sink.set_property("sync", False)
    rtcp_sink.set_property("async", False)
    rtcp_src = make("udpsrc", "rtcp_src")
    rtcp_src.set_property("port", a.feedback_port)
    rtcp_src.set_property("caps", Gst.Caps.from_string("application/x-rtcp"))

    for el in (src, demux, parse, pay, rtx, sess, drop, rtp_sink, rtcp_sink, rtcp_src):
        p.add(el)

    src.link(demux)

    def demux_pad(b, pad):
        if pad.get_name().startswith("video"):
            pad.link(parse.get_static_pad("sink"))
    demux.connect("pad-added", demux_pad)
    parse.link(pay)
    pay.link(rtx)

    # Link the RTCP feedback leg FIRST: the session's receive pads must be
    # active before the RTP side starts pushing, otherwise udpsrc is stopped.
    fb = sess.request_pad_simple("recv_rtcp_sink")
    rtcp_q = make("queue", "rtcp_q")
    p.add(rtcp_q)
    rtcp_q.get_static_pad("src").link(fb)
    link_ret = rtcp_src.get_static_pad("src").link(rtcp_q.get_static_pad("sink"))
    stats["rtcp_src_link_ret"] = getattr(link_ret, "value_nick", str(link_ret))
    probe_count(rtcp_src.get_static_pad("src"), stats, "rtcp_in_raw")
    probe_rtcp(fb, stats, "in")

    rtx.get_static_pad("src").link(sess.request_pad_simple("send_rtp_sink"))
    sess.get_static_pad("send_rtp_src").link(drop.get_static_pad("sink"))
    rtcp_pad = sess.request_pad_simple("send_rtcp_src")
    rtcp_pad.link(rtcp_sink.get_static_pad("sink"))
    probe_rtcp(rtcp_pad, stats, "out")

    drop.link(rtp_sink)
    probe_count(drop.get_static_pad("src"), stats, "rtp_sent")
    probe_rtp_pt(drop.get_static_pad("src"), stats, "out")
    stats["rtcp_src_port"] = rtcp_src.get_property("port")
    stats["rtcp_src_src_linked"] = int(rtcp_src.get_static_pad("src").is_linked())
    stats["fb_linked"] = int(fb.is_linked())
    HOLDER["fb"] = fb
    HOLDER["rtcp_src"] = rtcp_src

    # 可选：补一条 dummy RTP 接收腿，测试只发会话是否因此激活 NACK 处理
    if a.dummy_recv:
        dummy = make("udpsrc", "dummy")
        dummy.set_property("port", 5010)
        dummy.set_property("caps", Gst.Caps.from_string("application/x-rtp"))
        p.add(dummy)
        dummy.get_static_pad("src").link(sess.request_pad_simple("recv_rtp_sink"))
    return p, rtx, sess


def build_receiver(a, stats):
    p = Gst.Pipeline.new("receiver")
    rtp_src = make("udpsrc", "rtp_src")
    rtp_src.set_property("port", a.rtp_port)
    rtp_src.set_property(
        "caps",
        Gst.Caps.from_string(
            "application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000"),
    )
    sess = make("rtpsession", "sess")
    sess.set_property("rtp-profile", 3)  # AVPF（枚举：1=avp, 3=avpf）

    def ptmap_cb(_sess, _pt):
        return Gst.Caps.from_string(
            "application/x-rtp,media=video,encoding-name=H264,clock-rate=90000,"
            "rtcp-fb-nack=(boolean)true,rtcp-fb-nack-pli=(boolean)true")
    sess.connect("request-pt-map", ptmap_cb)

    rtx = make("rtprtxreceive", "rtxrecv")
    rtx.set_property("payload-type-map", pt_map_structure())
    demux = make("rtpssrcdemux", "demux")
    jb = make("rtpjitterbuffer", "jb")
    jb.set_property("latency", a.latency)
    jb.set_property("do-lost", True)
    jb.set_property("do-retransmission", not a.no_rtx)
    if not a.no_rtx:
        jb.set_property("rtx-max-retries", 8)
        jb.set_property("rtx-delay", 0)
        jb.set_property("rtx-min-delay", 0)
    try:
        jb.set_property("send-keyframe-request", True)
    except Exception:
        pass
    depay = make("rtph264depay", "depay")
    parse = make("h264parse", "parse")
    dec = make("avdec_h264", "dec")
    sink = make("fakesink", "sink")
    sink.set_property("sync", False)
    sink.set_property("async", False)
    rtcp_sink = make("udpsink", "rtcp_sink")
    rtcp_sink.set_property("host", a.host)
    rtcp_sink.set_property("port", a.feedback_port)
    rtcp_sink.set_property("sync", False)
    rtcp_sink.set_property("async", False)
    rtcp_src = make("udpsrc", "rtcp_src")
    rtcp_src.set_property("port", a.rtcp_port)
    rtcp_src.set_property("caps", Gst.Caps.from_string("application/x-rtcp"))

    for el in (rtp_src, sess, rtx, demux, jb, depay, parse, dec, sink, rtcp_sink, rtcp_src):
        p.add(el)

    probe_rtp_pt(rtp_src.get_static_pad("src"), stats, "net")
    rtp_src.get_static_pad("src").link(sess.request_pad_simple("recv_rtp_sink"))
    rtcp_pad = sess.request_pad_simple("send_rtcp_src")
    rtcp_pad.link(rtcp_sink.get_static_pad("sink"))
    probe_rtcp(rtcp_pad, stats, "out")
    probe_rtp_pt(sess.get_static_pad("recv_rtp_src"), stats, "in")

    # 隔离开关：跳过 rtprtxreceive，直接会话 -> demux -> jitterbuffer
    if a.no_rtxrecv:
        sess.get_static_pad("recv_rtp_src").link(demux.get_static_pad("sink"))
    else:
        sess.get_static_pad("recv_rtp_src").link(rtx.get_static_pad("sink"))
        rtx.link(demux)

    # demux 的 src pad 是按 SSRC 请求生成的，new-ssrc-pad 后再接到 jb
    def demux_pad(d, ssrc, pad):
        pad.link(jb.get_static_pad("sink"))
    demux.connect("new-ssrc-pad", demux_pad)
    jb.link(depay)
    depay.link(parse)
    parse.link(dec)
    dec.link(sink)
    probe_count(dec.get_static_pad("src"), stats, "decoded_frames")
    fb = sess.request_pad_simple("recv_rtcp_sink")
    rtcp_src.get_static_pad("src").link(fb)
    probe_count(rtcp_src.get_static_pad("src"), stats, "rtcp_in_raw")
    HOLDER["sess"] = sess
    HOLDER["jb"] = jb
    HOLDER["rtx"] = rtx
    HOLDER["demux"] = demux
    HOLDER["depay"] = depay
    HOLDER["parse"] = parse
    HOLDER["dec"] = dec
    return p, rtx, jb, sess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["sender", "receiver"])
    ap.add_argument("--file", default="/home/bai/rtc_test/clip10.mp4")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--rtp-port", type=int, default=5004)
    ap.add_argument("--rtcp-port", type=int, default=5006)
    ap.add_argument("--feedback-port", type=int, default=5005)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--latency", type=int, default=500)
    ap.add_argument("--no-rtx", action="store_true")
    ap.add_argument("--dummy-recv", action="store_true")
    ap.add_argument("--no-rtxrecv", action="store_true")
    ap.add_argument("--seconds", type=float, default=20.0)
    a = ap.parse_args()

    stats = {}
    if a.role == "sender":
        p, rtx, sess = build_sender(a, stats)
    else:
        p, rtx, jb, sess = build_receiver(a, stats)

    def session_stats():
        out = {}
        try:
            st = sess.get_property("stats")
            for i in range(st.n_fields()):
                nm = st.nth_field_name(i)
                if "nack" in nm or "rtx" in nm:
                    out[nm] = st.get_value(nm)
        except Exception as exc:
            out["err"] = str(exc)
        return out

    loop = GLib.MainLoop()

    def on_msg(bus, msg):
        if msg.type == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print("ERROR %s %s" % (err.message, dbg), flush=True)
            loop.quit()
        elif msg.type == Gst.MessageType.EOS:
            loop.quit()
        elif msg.type == Gst.MessageType.WARNING:
            err, _ = msg.parse_warning()
            print("WARN %s" % err.message, flush=True)

    bus = p.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_msg)

    if p.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
        print("FAILED", flush=True)
        return 2

    def stop():
        try:
            p.send_event(Gst.Event.new_eos())
        except Exception:
            pass
        return False

    def sample():
        fb = HOLDER.get("fb")
        src = HOLDER.get("rtcp_src")
        if fb is not None:
            stats["fb_active_at2s"] = int(fb.is_active())
        if src is not None:
            try:
                stats["srcpad_active_at2s"] = int(src.get_static_pad("src").is_active())
                stats["src_state_at2s"] = src.get_state(0)[1].value_nick
            except Exception as exc:
                stats["sample_err"] = str(exc)
        return False

    def force_key_unit():
        sess = HOLDER.get("sess")
        jb = HOLDER.get("jb")
        rtx = HOLDER.get("rtx")
        demux = HOLDER.get("demux")
        depay = HOLDER.get("depay")
        parse = HOLDER.get("parse")
        dec = HOLDER.get("dec")
        ssrc = stats.get("ssrc")
        if sess is not None and jb is not None and ssrc is not None:
            try:
                st = Gst.Structure.new_empty("GstForceKeyUnit")
                v = GObject.Value()
                v.init(GObject.TYPE_UINT)
                v.set_uint(ssrc)
                st.set_value("ssrc", v)
                v2 = GObject.Value()
                v2.init(GObject.TYPE_UINT)
                v2.set_uint(96)
                st.set_value("payload", v2)
                v3 = GObject.Value()
                v3.init(GObject.TYPE_BOOLEAN)
                v3.set_boolean(False)
                st.set_value("all-headers", v3)
                targets = []
                for el in (dec, parse, depay, jb, demux, rtx):
                    if el is not None:
                        pad = el.get_static_pad("sink")
                        if pad is not None:
                            targets.append(pad)
                ok = False
                for pad in targets:
                    ev = Gst.Event.new_custom(
                        Gst.EventType.CUSTOM_UPSTREAM, st.copy())
                    if pad.push_event(ev):
                        ok = True
                        break
                stats["force_key_unit_sent"] = int(ok)
            except Exception as exc:
                stats["force_key_unit_err"] = str(exc)
        return False

    GLib.timeout_add(2000, sample)
    if a.role == "receiver":
        GLib.timeout_add(3000, force_key_unit)
    GLib.timeout_add(int(a.seconds * 1000), stop)
    GLib.timeout_add(int((a.seconds + 5) * 1000), lambda: (loop.quit(), False)[1])

    loop.run()
    p.set_state(Gst.State.NULL)

    result = {"role": a.role, "loss": a.loss, "no_rtx": a.no_rtx, "stats": stats}
    if a.role == "sender":
        result["rtxsend"] = {
            "requests": rtx.get_property("num-rtx-requests"),
            "packets": rtx.get_property("num-rtx-packets"),
        }
    else:
        result["rtxrecv"] = {
            "requests": rtx.get_property("num-rtx-requests"),
            "packets": rtx.get_property("num-rtx-packets"),
            "assoc": rtx.get_property("num-rtx-assoc-packets"),
        }
        st = jb.get_property("stats")
        d = {}
        for i in range(st.n_fields()):
            nm = st.nth_field_name(i)
            d[nm] = st.get_value(nm)
        result["jitterbuffer"] = d

    result["session"] = session_stats()
    print("RESULT " + json.dumps(result, default=str), flush=True)
    import os
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
```

### 10.2 `tools/run_t7.sh`

```bash
#!/bin/bash
# T7 A/B arm runner: arg1 = loss probability, arg2 = seconds
export GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
LOSS=${1:-0.0}
SEC=${2:-20}
NO_RTX=${3:-}
NO_RTX_FLAG=""
if [ "$NO_RTX" = "no-rtx" ]; then NO_RTX_FLAG="--no-rtx"; fi
pkill -f t7_rtx_lab.py 2>/dev/null
sleep 1

python3 /tmp/t7_rtx_lab.py receiver --file /home/bai/rtc_test/clip10.mp4 --host 127.0.0.1 \
  --rtp-port 5004 --rtcp-port 5006 --feedback-port 5005 --loss 0.0 --latency 500 \
  $NO_RTX_FLAG --seconds "$SEC" > /tmp/recv_t7.log 2>&1 &
RPID=$!
sleep 2
python3 /tmp/t7_rtx_lab.py sender --file /home/bai/rtc_test/clip10.mp4 --host 127.0.0.1 \
  --rtp-port 5004 --rtcp-port 5006 --feedback-port 5005 --loss "$LOSS" --latency 500 \
  --seconds "$SEC" > /tmp/send_t7.log 2>&1 &
SPID=$!
wait "$SPID" "$RPID" 2>/dev/null

echo "=== RECEIVER ==="
cat /tmp/recv_t7.log
echo "=== SENDER ==="
cat /tmp/send_t7.log
```

### 10.3 `tools/inspect_rtpsession.py`

```python
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject
Gst.init(None)

for name in GObject.signal_list_names(Gst.Element):
    if "key" in name.lower() or "pli" in name.lower() or "fir" in name.lower():
        print("Element signal:", name)

el = Gst.ElementFactory.make("rtpsession", "x")
print("rtpsession signals:")
for sig in GObject.signal_list_names(type(el)):
    print(" -", sig)
print("actions:")
for prop in ("request-pt-map",):
    print(prop)
```

## 11. 相关本地文件

- `T7_NACK_RTX_PLI_STATUS_20261115.md`：简版 T7 状态台账。
- `tools/t7_rtx_lab.py`：裸 `rtpsession` T7 实验台。
- `tools/rtp_media_lab.py`：`rtpbin` 版 RTP/RTX/jb 实验台；profile 已修为 3；aux 元件由信号回调 add，不提前加入管线。
- `tools/run_t7.sh`：A/B/C 三臂 runner。
- 本地源码：`gst-plugins-good-1.26.2/gst/rtpmanager/`。
