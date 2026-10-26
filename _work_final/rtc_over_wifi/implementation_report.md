# RTC over WiFi（去掉 UDP/IP）实现与测试报告

日期：2026-10-26
项目：BPI-R4 OpenWrt + Windows/Linux 客户端

## 1. 结论

已实现并测试通过：

- 自定义 EtherType 0x88B5，直接跑在 802.11 L2 上；
- 不使用 IPv4/IPv6、UDP、TCP；
- H.264 视频分片、重组、解码正常；
- 实时 30 fps 帧级 pacing；
- 双向 PC→AP；
- 两个 STA 经 AP bridge；
- XOR FEC 丢包恢复；
- NACK 缓存重传；
- 真实摄像头 5G/2.4G 场景。

因此：

- 如果目标是“客户端使用新设计的 RTC over WiFi 协议栈传输视频”：**可行，已实现**；
- 如果目标是“标准 WebRTC/浏览器/手机 App 在没有 IP/UDP 的情况下直接互通”：**不可行**，原因见第 8 节。

## 2. 实现方法

### 2.1 协议栈

    H.264 (AUD 帧边界)
    RTC 头：magic / seq / len / flags / rsv
    FEC：K=8 数据块 + 1 个 XOR parity
    NACK：接收端请求，发送端缓存重传
    L2：EtherType 0x88B5
    802.11 WMM / WPA2
    WiFi PHY

没有 IP/UDP/TCP。

### 2.2 帧头

    struct hdr {
      uint32_t magic;   // RTC1 = 0x52544331
      uint32_t seq;
      uint16_t len;
      uint16_t flags;   // bit0 = FEC parity
      uint32_t rsv;     // group id 或时间戳
    };

### 2.3 发送端

- 板端 C：AF_PACKET + SOCK_RAW；
- 发送接口：phy0.1-ap0（5G AP）或 phy0.0-ap0（2.4G AP）；
- 目的 MAC：接收 STA 的 MAC；
- H.264 按 AUD 分帧；
- 每帧按 1200 B 分片；
- 30 fps：每帧后 sleep 33 ms；
- FEC：每 8 个数据块生成 1 个 XOR parity；
- NACK：发送后缓存 3 s，收到 NACK:seq 重传对应块。

### 2.4 接收端

- Windows：Npcap + Scapy，过滤 EtherType 0x88B5；
- 按 seq 重组；
- 缺失块：
  - FEC：用 parity 恢复 1 个丢块；
  - NACK：发 NACK:seq 请求重传；
- 写 H.264 文件；
- ffmpeg 解码验证。

### 2.5 无 IP/UDP 的证明

抓包只看到：

    36:19:86:e0:2e:0f > 90:de:80:1c:6a:7a (0x88b5) / Raw

payload 从以太网头后直接是 RTC 头，没有 IPv4/IPv6/UDP/TCP 头。

## 3. 测试方法

### 3.1 拓扑 A：AP 端点

    BPI-R4 5G AP (phy0.1-ap0) --WiFi--> PC WLAN3

- AP 发送，PC 接收；
- 管理走以太网 192.168.240.2；
- PC WLAN3 192.168.240.126。

### 3.2 拓扑 B：两个 STA 经 AP bridge

    PC WLAN3 --WiFi--> BPI-R4 AP bridge --WiFi--> PC 自带 WLAN

- WLAN3 发送；
- 自带 WLAN 接收；
- AP 只做 L2 bridge。

### 3.3 测试项

1. 最小 H.264 文件传输；
2. 实时 30 fps 帧级传输；
3. 双向 PC→AP + ACK；
4. 两 STA bridge；
5. FEC 丢块恢复；
6. NACK 丢块重传；
7. 真实摄像头 5G/2.4G/背景负载。

### 3.4 判定

- 接收端能否重组；
- ffmpeg 能否解码；
- 帧数/字节数；
- 丢块数；
- SHA256 是否与原始一致；
- 抓包是否只有 0x88B5、没有 IP/UDP。

## 4. 原始测试数据

### 4.1 最小视频传输

发送：

    /root/l2video_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test.h264 1200
    sent 64 chunks, iface=phy0.1-ap0

接收：

    chunks 64 max 63
    missing 0 bytes 76456

解码：

    frame=   90 fps=0.0 q=-0.0 Lsize=N/A time=00:00:03.00

### 4.2 实时 30 fps 帧级

发送：

    sent 90 frames 97 chunks in 3005 ms fps=30

接收：

    chunks 97 max 96 span 2.97
    missing 0 bytes 69414

解码：

    frame=   90 fps=0.0 q=-0.0 Lsize=N/A time=00:00:03.00

### 4.3 双向 PC→AP

板端：

    listening iface=phy0.1-ap0 ack=1
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_0
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_1
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_2
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_3
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_4

PC 收到：

    ACK 36:19:86:e0:2e:0f > 90:de:80:1c:6a:7a (0x88b5) / Raw
    ... 共 5 个

### 4.4 两 STA 经 AP bridge

    90:de:80:1c:6a:7a > c0:35:32:19:cc:fb (0x88b5) / Raw
    b'BRIDGE_TEST_0'
    b'BRIDGE_TEST_1'
    b'BRIDGE_TEST_2'
    b'BRIDGE_TEST_3'
    b'BRIDGE_TEST_4'

5 帧全部转发。

### 4.5 FEC

发送：

    /root/l2fec_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264
    fec sent groups=8 frames=66

接收（故意丢 seq=5）：

    deliberately dropped seq 5
    data 57 parity 8
    recovered 5 len 1200
    bytes 69414 missing 7 sha da4222b1b9a654fd

原始/恢复 SHA256：

    DA4222B1B9A654FD57A90D734D743072FEB3755E397F2CB9F0704543C0740D94
    DA4222B1B9A654FD57A90D734D743072FEB3755E397F2CB9F0704543C0740D94

完全一致。

说明：missing 7 是 parity 帧序号不参与数据拼接，不是 7 个数据块丢失。

### 4.6 NACK

发送：

    sent 58 chunks, waiting NACK 3s
    NACK 5 -> resend
    done resent=2

接收：

    drop seq5, send NACK
    got retransmit seq5
    chunks 58 nack True max 57
    bytes 69414 missing 0 sha da4222b1b9a654fd

原始/恢复 SHA256 完全一致。

### 4.7 真实摄像头

摄像头：Integrated Camera 640x480 @30fps，H.264 约 8 Mbit/s。

    | 场景 | chunk | 丢失 | 接收字节 | 接收跨度 | 解码帧 |
    | 5G 空闲 | 5754 | 0 | 6,584,449 | 6.439 s | 181 |
    | 5G + 322 Mbit/s 背景 | 5011 | 0 | 5,678,619 | 6.461 s | 181 |
    | 2.4G | 4979 | 25 | 5,650,042 | 6.494 s | 181 |

结论：

- 5G 空闲/背景负载 0 丢块；
- 2.4G 约 0.5% 丢块，视频仍可解码，需要 FEC/NACK；
- 真实摄像头 181 帧/6 s，约 30 fps。

## 5. 测试结果分析

- 最小 demo：视频 90 帧、76,456 B、0 丢块，接收端可解码；
- 实时：90 帧/3.005 s，接收 span 2.97 s，0 丢块；
- 双向：5 帧 PC→AP，5 个 ACK；
- bridge：5 帧跨 STA 转发；
- FEC：丢 1 块恢复，SHA 一致；
- NACK：丢 seq5 重传，SHA 一致；
- 真实摄像头：5G 0 丢块；2.4G 0.5% 丢块，FEC/NACK 是必需的。

## 6. 实现文件

    _work_final/rtc_over_wifi/
      l2video_send_rt.c      实时 30fps 发送
      l2video_recv_rt.py     接收/重组/统计
      l2fec_send.c           FEC 发送
      l2fec_recv.py          FEC 接收/恢复
      l2nack_send.c          NACK 发送/缓存重传
      l2nack_recv.py         NACK 接收/请求
      l2send.c               最小 L2 发送
      l2recv.c               板端 L2 接收/ACK
      live_cam_send.py       真实摄像头发送
      live_cam_recv.py       真实摄像头接收
      test.h264              测试视频
      test_aud.h264          AUD 测试视频
      recv_rt_first.png      实时接收首帧
      recv_live_first.jpg    真实摄像头接收帧

## 7. 适用边界

   单 AP / 单 L2 域
   两端 Linux/OpenWrt/专用硬件
   有 raw socket 权限
   视频单向/双向
   WPA2 链路加密

不做：

- 浏览器/手机 App 直连（无 raw L2 权限）；
- 跨 AP/公网/NAT（没有 IP 路由）；
- 标准 WebRTC 互通（依赖 ICE/UDP）；
- DTLS/SRTP 端到端加密（v1 用 WPA2）；
- 自适应拥塞控制（v1 固定 30 fps）。

## 8. 为什么标准 WebRTC/手机不可行

1. 浏览器 WebRTC API 只暴露 IP/UDP/ICE，不能发 raw 802.11 帧；
2. Android/iOS App 无 raw L2 权限，VPNService 只到 IP 层；
3. 没有 IP 就没有 NAT/路由，跨 AP/公网不可达；
4. 标准 WebRTC 端点需要 ICE/DTLS/SRTP over UDP；
5. 需要两端都实现自定义协议。

因此本方案是“边缘专用 RTC over WiFi”，不是标准 WebRTC 替代品。

## 9. 与 SparkRTC 的关系

SparkRTC 基于 WebRTC，仍是 UDP/IP 传输。  
本方案不复用其传输层；只参考其媒体 pipeline/GCC/FEC。  
v1 用轻量自定义帧头 + FEC + NACK 已经跑通视频。

## 10. 最终结论

- 边缘单 L2 域：**可行，已实现并测试**；
- 最小 demo：**接收端视频正常**；
- 实时、双向、bridge、FEC、NACK：**全部实测通过**；
- 真实摄像头 5G/2.4G：**已验证**；
- 标准 WebRTC/手机/浏览器：**不可行，明确不在范围内**。
