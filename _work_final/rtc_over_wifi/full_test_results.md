# RTC over WiFi 全功能测试与最终方案（2026-10-26）

## 0. 测试结论

| 功能 | 结果 |
|---|---|
| 自定义 EtherType L2 视频 | 通过 |
| 实时 30 fps 帧级 pacing | 通过（90 帧/3.005 s，接收 span 2.97 s） |
| 双向 PC→AP | 通过（板端收到 5 帧，PC 收到 5 个 ACK） |
| 两个 STA 经 AP bridge | 通过（WLAN3→AP→WLAN，5 帧全部转发） |
| FEC 丢包恢复 | 通过（故意丢 1 个数据块，XOR 恢复，SHA256 完全一致） |
| NACK 重传 | 通过（故意丢 seq5，NACK 后重传，SHA256 完全一致） |
| 拥塞控制 | v1 固定 30 fps pacing（自适应 CC 不在 v1） |
| DTLS/SRTP 端到端加密 | 不在 v1（仅 WPA2 链路加密） |
| 手机/浏览器直接参与 | 不可行（无 raw L2 权限/WebRTC 依赖 IP） |

结论：**边缘单 L2 域的自定义 RTC 视频传输可行，且已跑通实时、双向、桥接、FEC、NACK；完整 WebRTC/DTLS-SRTP/手机浏览器不是当前架构能直接支持的。**

## 1. 环境

- BPI-R4 OpenWrt 24.10，5G AP phy0.1-ap0，HE80，ch149；
- PC Windows：WLAN3 MediaTek（192.168.240.126）作为 STA；
- 第二 STA：PC 自带 Realtek 8852CE（192.168.240.147），仅用于 bridge 测试；
- 管理：以太网 192.168.240.2；
- 自定义 EtherType：0x88B5；
- 板端：AF_PACKET + SOCK_RAW；
- PC 端：Npcap + Scapy。

## 2. 实时 30 fps 帧级传输

H.264 文件带 AUD，90 帧，3 秒，640x360。

发送端：

    /root/l2video_send_rt phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264 30

输出：

    sent 90 frames 97 chunks in 3005 ms fps=30

接收端：

    chunks 97 max 96 span 2.97
    missing 0 bytes 69414

解码：

    frame=   90 fps=0.0 q=-0.0 Lsize=N/A time=00:00:03.00

说明：

- 按 AUD 分帧，每帧后 sleep 33 ms；
- 90 帧实际发送 3.005 s，接收跨度 2.97 s；
- 97 个 chunk 全部到达；
- 90 帧全部可解码。

## 3. 双向 PC→AP

板端：

    /root/l2recv phy0.1-ap0 ack

板端输出：

    listening iface=phy0.1-ap0 ack=1
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_0
    ...
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_4

PC 端收到：

    ACK 36:19:86:e0:2e:0f > 90:de:80:1c:6a:7a (0x88b5) / Raw
    ... 共 5 个

结论：PC→AP 自定义帧可达，AP→PC ACK 可达，双向反馈链路成立。

## 4. 两个 STA 经 AP bridge

拓扑：

    PC WLAN3 (90:de:80:1c:6a:7a)  --WiFi-->  BPI-R4 AP  --WiFi-->  PC WLAN (c0:35:32:19:cc:fb)

WLAN3 发送 EtherType 0x88B5，目的 MAC 为 WLAN 的 MAC。

在 WLAN 上抓到：

    90:de:80:1c:6a:7a > c0:35:32:19:cc:fb (0x88b5) / Raw
    b'BRIDGE_TEST_0'
    ...
    b'BRIDGE_TEST_4'

5 帧全部转发。  
说明 AP 的 Linux bridge 不会丢未知 EtherType；两个 STA 经 AP 的 L2 转发可行。

## 5. FEC 丢包恢复

发送端：

    /root/l2fec_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264

- K=8 数据块 + 1 个 XOR parity；
- 8 组，66 帧；
- 接收端故意丢弃 seq=5。

接收端：

    deliberately dropped seq 5
    data 57 parity 8
    recovered 5 len 1200
    bytes 69414 missing 7 sha da4222b1b9a654fd

原始文件 SHA256：

    DA4222B1B9A654FD57A90D734D743072FEB3755E397F2CB9F0704543C0740D94

恢复文件 SHA256：

    DA4222B1B9A654FD57A90D734D743072FEB3755E397F2CB9F0704543C0740D94

**完全一致。** 一个数据块丢失可由 XOR parity 恢复。

## 6. 未实现/不可行项

### 6.1 NACK 重传（已测试）

发送端：

    /root/l2nack_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264

接收端故意丢弃 seq=5，然后发 NACK:5；发送端缓存 58 个 chunk，收到后重传。

板端输出：

    sent 58 chunks, waiting NACK 3s
    NACK 5 -> resend
    done resent=2

接收端：

    drop seq5, send NACK
    got retransmit seq5
    chunks 58 nack True max 57
    bytes 69414 missing 0 sha da4222b1b9a654fd

原始/恢复 SHA256 完全一致。

NACK 反馈帧与 ACK 走同一 EtherType 0x88B5，方向 STA→AP→发送端。

### 6.2 拥塞控制

当前是固定 30 fps pacing，没有根据 RTT/丢包/队列调整码率。

可行设计：

- 接收端每 20 ms 回反馈：收到帧号、丢包、延迟；
- 发送端用 GCC 简化版/延迟梯度调整发送速率；
- 与 802.11 队列/airtime 联动。

v1 不包含自适应 CC：固定 30 fps pacing + FEC/NACK 已能覆盖当前视频码率；自适应 CC 是 v2 增强，不是可行性阻塞项。

### 6.3 DTLS/SRTP 端到端加密

v1 只依赖 WPA2 链路加密；没有 DTLS 握手/SRTP。

原因：

- WebRTC 的 DTLS/SRTP 默认跑在 UDP 上；
- 要用在 L2 上，需要把 DTLS/SRTP 的 datagram transport 换成自定义 L2 transport；
- 需要引入 OpenSSL/mbedTLS + SRTP 库，并重写握手/密钥/重放窗口；
- 工作量明显大于本周 demo。

当前安全边界：**WPA2 链路加密**，不是端到端。

### 6.4 手机/浏览器直接参与

不可行：

- 浏览器 WebRTC 只暴露 ICE/UDP，不能发 raw 802.11；
- Android/iOS App 无 raw L2 权限（VPNService 只到 IP）；
- 没有 IP 就没有 NAT/路由，跨 AP/公网不可达；
- 需要两端都实现自定义协议。

因此最终方案必须明确：**这是边缘可控设备方案，不是通用 WebRTC 替代品。**

## 7. 最终方案（建议）

### 7.1 适用边界

   单 AP / 单 L2 域
   两端为 Linux/OpenWrt/专用硬件
   视频单向或双向
   可接受 WPA2 链路加密
   不做公网/NAT/浏览器互通

### 7.2 协议栈

   视频 codec (H.264/VP8)
   RTC 帧头：stream_id / seq / frame_id / frag / ts / flags
   FEC：XOR 或 Reed-Solomon
   反馈：ACK/NACK/延迟
   L2：EtherType 0x88B5
   802.11 QoS/WMM
   WPA2/3

### 7.3 唯一交付线路（v1，已完成）

    H.264 + AUD 帧边界
    RTC 头（seq/len/flags）
    XOR FEC（K=8 + 1 parity）
    NACK 缓存重传（58 chunk 缓存）
    EtherType 0x88B5
    802.11 WMM + WPA2

已验证：

- 实时 30 fps（90 帧/3.005 s）；
- 双向 PC→AP；
- 两 STA 经 AP bridge；
- FEC 丢 1 块恢复；
- NACK 丢 seq5 重传恢复；
- 接收端解码 90 帧正常。

### 7.4 不在 v1 范围

- 自适应拥塞控制（v1 固定 30 fps）；
- DTLS/SRTP 端到端加密（v1 用 WPA2 链路加密）；
- 手机/浏览器直连；
- 跨 AP/公网/NAT；
- SparkRTC 完整接入。

这些不是“方案失败”，而是明确的产品边界；如需，另立 v2，不改 v1 主线路。

## 8. 最终判断

- **技术上可行**：边缘单 L2 域、自定义端点、视频传输已经实测通过；
- **v1 工程闭环**：视频、实时、双向、桥接、FEC、NACK 均已实测；
- **明确不做**：自适应 CC、DTLS/SRTP、手机/浏览器；
- **产品边界**：不能替代标准 WebRTC，不能直接支持手机/浏览器；
- **推荐定位**：边缘专用 L2 视频链路，而不是通用 RTC 协议。

