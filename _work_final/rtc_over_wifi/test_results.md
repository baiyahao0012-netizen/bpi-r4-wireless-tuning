# RTC over WiFi 最小 Demo 实测结果（2026-10-26）

## 1. 结论

**已实测通过：自定义 EtherType 0x88B5 的 H.264 视频帧，经 BPI-R4 5G AP → PC WLAN3 真实 WiFi 链路传输，接收端完整还原 90 帧/3 秒，无 IP/UDP。**

这是“视频能正常传输”的最小验证，不是完整 RTC：还没有实时 pacing、FEC、拥塞控制、双向/多 STA。

## 2. 拓扑

```text
BPI-R4 5G AP (phy0.1-ap0)  --WiFi-->  PC WLAN3 (192.168.240.126)
        |                                      |
        | 以太网管理                            | Npcap/Scapy 收包
        +--------------------------------------+
```

- AP：`phy0.1-ap0`，ch149 HE80，MAC `36:19:86:e0:2e:0f`；
- PC：WLAN3 MediaTek，MAC `90:de:80:1c:6a:7a`；
- 自带 WLAN 断开；WLAN5 不在列表；
- 管理走以太网 `192.168.240.2`。

## 3. 帧格式

```c
struct hdr {
  uint32_t magic;   // 'RTC1' = 0x52544331
  uint32_t seq;     // chunk 序号
  uint16_t len;     // payload 长度
  uint16_t flags;
  uint32_t rsv;
};
```

- EtherType：`0x88B5`；
- 以太网头 14 B + RTC 头 16 B + payload；
- payload 1200 B/chunk；
- 发送端 `AF_PACKET + SOCK_RAW`；
- 接收端 Npcap + Scapy 过滤 `ether proto 0x88b5`，按 seq 重组。

## 4. 实测

发送端（板端）：

```sh
/root/l2video_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test.h264 1200
```

输出：

```text
sent 64 chunks, iface=phy0.1-ap0
```

接收端：

```text
chunks 64 max 63
missing 0 bytes 76456
```

原始 H.264 76,456 B，接收 76,456 B，64 个 chunk 全部到达、顺序重组正确。

ffmpeg 解码：

```text
frame=   90 fps=0.0 q=-0.0 Lsize=N/A time=00:00:03.00
```

- 640×360，30 fps，3 s，90 帧；
- 无解码错误；
- 首帧已保存为 `recv_first.png`（彩条测试图）。

## 5. 无 IP/UDP 的证据

- 发送帧 EtherType 固定 `0x88B5`；
- 接收端只接受 `Ether` 且 `type == 0x88B5`；
- Npcap 抓到的帧：

```text
36:19:86:e0:2e:0f > 90:de:80:1c:6a:7a (0x88b5) / Raw
```

- payload 从以太网头后直接是 RTC 头，没有 IPv4/IPv6、没有 UDP/TCP 头；
- 该路径没有经过 IP 栈。

## 6. 已验证 / 未验证

### 已验证

- 真实 5G WiFi AP→STA 自定义 EtherType 收发；
- AF_PACKET 发送、Npcap 接收；
- 自定义头 + 分片/序号重组；
- H.264 文件完整传输、可解码；
- 不需要 IP/UDP。

### 未验证

- 实时 30 fps pacing / 播放；
- 双向（PC→AP）；
- 两个 STA 经 AP bridge；
- FEC/NACK/拥塞控制；
- DTLS/SRTP/端到端加密（当前依赖 WPA2 链路加密）；
- 手机/浏览器直接参与。

## 7. 修正后的本周方案

1. **保留当前 AP→PC 单向 demo 作为基线**；
2. 把发送端改成按 30 fps 实时发送（帧边界、时间戳、pacing）；
3. 接收端加 jitter buffer + `ffplay`/GStreamer 播放；
4. 测 FPS、丢帧、端到端时延；
5. 再做 PC→AP 反向；
6. 最后做两个 STA 经 AP bridge；
7. SparkRTC 只在传输层跑通后再评估接入。

## 8. 关键结论

- **RTC over WiFi（去掉 IP/UDP）在边缘单 L2 域可行**；
- 真实 WiFi 上自定义 EtherType 视频已跑通；
- 但“完整 WebRTC/浏览器/手机”仍不可行；
- 当前是 L2 视频传输原型，不是生产 RTC。
