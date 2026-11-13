## 先回答：功能清单上，是的

按 L0 的媒体层功能清单：

| 项 | 状态 |
|---|---|
| T1 解码 | 通过 |
| T2 RTP 头 | 通过 |
| T3 严格 302/302 | **已闭环** |
| T4 SRTP 302/302、5933 包、0 drop | **已闭环** |
| T5 RTCP SR | 通过 |
| T6 乱序重排 | 通过 |
| T7 NACK/PLI/RTX | **缺** |
| T8 音频 jb + rtpbin A/V | **缺** |
| T9 PSNR/SSIM | 通过 |

所以：

> **开源 RTC 媒体层的功能项，目前确实主要缺 T7、T8 两项。**

但如果把“开源 RTC 层”理解成可交付的完整层，还缺这些工程项：

- SRTP 生产密钥协商（当前固定测试 key）；
- 实时采集/编码/pacing；
- RTCP 接收端 RR/反馈闭环；
- Windows/笔记本正式接收端集成；
- L2 的正式 `l2sink/l2src` 和可靠性补丁。

---

## 一、T7 的开源参考

### 1. GStreamer 官方 `rtprtxreceive` 示例

GStreamer 官方给了一个完整的发送/接收 + 丢包 + RTX 示例：

- 发送端：

```text
rtpsession rtp-profile=avpf
  ! rtprtxsend payload-type-map="application/x-rtp-pt-map,96=(uint)97"
  ! identity drop-probability=0.01
  ! udpsink
```

- 接收端：

```text
rtpsession rtp-profile=avpf
  ! rtprtxreceive payload-type-map="application/x-rtp-pt-map,96=(uint)97"
  ! rtpssrcdemux
  ! rtpjitterbuffer do-retransmission=true
  ! rtpopusdepay ...
```

官方说明：

- `rtpjitterbuffer do-retransmission=true` 会向上游发 `GstRTPRetransmissionRequest`；
- `rtpsession` 把它转成 RTCP NACK；
- 发送端 `rtprtxsend` 用新的 SSRC/PT 重传；
- 接收端 `rtprtxreceive` 把 RTX 流还原成原 SSRC/PT。

参考：[rtprtxreceive 官方文档](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtprtxreceive.html?gi-language=python)

### 2. 官方更推荐 `rtpbin` 的 aux 信号

官方明确说：

> 通常应避免手写 `rtprtxsend/rtprtxreceive` 管线，改用 `rtpbin` 的 `request-aux-sender` / `request-aux-receiver` 信号。

也就是说，T7 的正确实现不是 `gst-launch`，而是：

```text
rtpbin
  + request-aux-sender
  + request-aux-receiver
  + rtprtxsend/rtprtxreceive
  + rtpjitterbuffer do-retransmission
```

参考：[rtpbin 文档](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpbin.html)

### 3. 社区 Python + rtpbin + RTX 实例

GStreamer devel 邮件列表里有一个实际实现：

- 用 Python 搭 RTP server/client；
- 在 rtpbin 内使用 `rtprtxsend` / `rtprtxreceive`；
- `do-retransmission=true`；
- 观察 RTX 请求和响应。

参考：[GStreamer devel: RTP and retransmission](https://lists.freedesktop.org/archives/gstreamer-devel/2015-November/055471.html)

### 4. 更简单的 `rtprtxqueue`

如果暂时不做 RFC 4588 的独立 RTX SSRC，可以用：

```text
rtprtxqueue
```

它缓存已发 RTP，收到重传请求后原样重发；接收端 `rtpjitterbuffer` 可以直接恢复，不需要 `rtprtxreceive`。

参考：[rtprtxqueue 文档](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtprtxqueue.html)

适合先验证“选择性重传是否有效”，再升级到标准 RTX。

### 5. Pion 的 NACK/RTX 实现

Go/Pion 有明确的 NACK/RTX 互操作测试：

- 故意丢第 2 个包；
- 期望恰好 1 个 NACK、1 个 RTX；
- 用于验证“单次丢失只触发一次恢复”。

参考：[Pion NACK/RTX test PR](https://github.com/pion/webrtc/pull/3270/files/4a6020de5d26a0fdde7369c8c6c676c90da88949)

这个可以作为 T7 的**验收行为参考**：不是“有重传就行”，而是要验证 NACK/RTX 的次数和关联。

---

## 二、T8 的开源参考

### 1. GStreamer `rtpbin` 的双 session

`rtpbin` 本身就是为多流设计的：

```text
rtpbin name=r
  session 0 = 视频
  session 1 = 音频
```

每个 session 有自己的：

- `recv_rtp_sink_0/1`
- `recv_rtcp_sink_0/1`
- `send_rtcp_src_0/1`
- jitterbuffer

音频和视频各自 `rtpjitterbuffer`，再用 RTCP SR 的 NTP↔RTP 映射统一到同一时钟。

参考：[rtpbin 文档](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpbin.html)

### 2. `rtpjitterbuffer` 的同步参数

T8 需要关注：

```text
do-retransmission
rtx-delay
rtx-max-retries
latency
mode
ts-offset
```

其中 `do-retransmission` 和 RTX 参数同时服务 T7。

参考：[rtpjitterbuffer 文档](https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpjitterbuffer.html)

### 3. aiortc 的 JitterBuffer

Python 实现可参考 aiortc：

- `JitterBuffer` 按 seq/timestamp 重排；
- 处理乱序、丢包、PLI；
- 音频/视频共用同一套时间轴。

参考：[aiortc 仓库](https://github.com/aiortc/aiortc)

它不是 GStreamer 实现，但可以作为 T8 的算法对照。

### 4. 生产级参考：Janus / mediasoup

如果需要更完整的 RTCP SR、NACK、A/V sync 设计，可参考：

- Janus WebRTC Server；
- mediasoup；
- Pion。

这些项目的共同点：

- RTCP SR 做 NTP↔RTP；
- 音频主时钟，视频跟随；
- NACK/RTX 与 jitterbuffer 联动；
- 不把音频和视频各自独立播放。

---

## 三、落地建议

### T7

```text
1. rtpbin 双端
2. request-aux-sender / request-aux-receiver
3. rtprtxsend / rtprtxreceive
4. rtpjitterbuffer do-retransmission=true
5. identity drop-probability=0.01~0.05
6. RTCP 探针看 205/206
7. 读 num-rtx-requests/num-rtx-packets/num-rtx-assoc-packets
```

验收：

```text
NACK(205) 出站
RTX 包被接收端关联
丢包恢复臂优于关闭臂
不是“有 RTX 包”就算过，要验证关联和恢复
```

### T8

```text
1. rtpbin 两个 session
2. 视频/音频各自 jitterbuffer
3. RTCP SR 的 NTP↔RTP
4. 音频 sink 为主时钟
5. PC/Pi 对同一 NTP 源记录 offset
6. 锚点素材测 A/V skew
```

验收：

```text
音频 jb 不滞留
A/V p95 ≤ 40 ms
跨机时钟偏移纳入误差
```

---

## 四、一句话

**功能清单上，现在主要缺 T7、T8；开源参考很明确：GStreamer 官方 `rtpbin + rtprtxsend/rtprtxreceive + rtpjitterbuffer do-retransmission` 对应 T7，`rtpbin` 双 session + RTCP SR 对应 T8。Pion 和 aiortc 可作为行为和算法对照。**

下一步应按官方推荐，用 `rtpbin` 的 `request-aux-sender/receiver` 实现 T7，而不是继续用 `gst-launch` 拼最小管线。