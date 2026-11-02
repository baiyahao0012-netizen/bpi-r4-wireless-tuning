# RTC over WiFi（去掉 IP/UDP）技术可行性、硬件验证与交付文档

版本：v1.0  
日期：2026-10-30  
平台：BPI-R4 OpenWrt 24.10 + MT7996 BE14 + Windows PC

---

## 1. 结论摘要

### 1.1 技术结论

在“单一 802.11 L2 域 + 两端可控 Linux/OpenWrt 设备”的边缘场景下：

- 可以去掉 IPv4/IPv6、UDP、TCP；
- 可以用自定义 EtherType 0x88B5 在 802.11 L2 上传输 H.264；
- 可以实现视频分片、重组、实时 30 fps、双向 ACK、AP bridge、FEC、NACK；
- 不能与标准 WebRTC/浏览器/手机 App 直接互通；
- 不支持跨 AP/公网/NAT；
- 不是完整 WebRTC 替代品。

### 1.2 硬件结论

- BPI-R4 + MT7996 支持 AF_PACKET raw socket；
- 支持自定义 EtherType 收发；
- AP bridge 可转发自定义 EtherType（两个 STA 之间）；
- 5G/2.4G 均可承载 H.264；
- 5G 空闲/背景负载下 0 丢块；
- 2.4G 出现约 0.5% chunk 丢失，需要 FEC/NACK；
- 手机/浏览器没有 raw L2 权限，不能直接作为端点。

---

## 2. 硬件与软件环境

### 2.1 硬件

- 开发板：Banana Pi BPI-R4 2.5GE PoE
- SoC：MediaTek MT7988A
- 内存：4 GB
- 无线：MediaTek MT7996（WiFi 7，BE14）
- 存储：SD 卡
- 管理：以太网
- 客户端：Windows PC + MediaTek USB WiFi + Realtek 8852CE

### 2.2 软件

- OpenWrt 24.10.0
- Revision r28427-6df0e3d02a
- Linux 6.6.73
- 目标：mediatek/filogic
- 板端：AF_PACKET + SOCK_RAW
- PC 端：Npcap + Scapy
- 视频：H.264，AUD，zerolatency
- 解码：ffmpeg

### 2.3 官方链接

- BPI-R4 产品页：
  https://banana-pi.org/web/index.php?topclassid=19&classid=83&id=539&lanstr=en&wap=1
- BPI-R4 Wiki：
  https://wiki.banana-pi.org/Getting_Started_with_BPI-R4
- OpenWrt 设备页：
  https://openwrt.org/inbox/toh/sinovoip/bananapi_bpi-r4
- SparkRTC 参考：
  https://github.com/hkust-spark/sparkrtc

---

## 3. 范围定义：“去掉 IP/UDP”到底去掉什么

保留：

- 802.11 MAC/LLC；
- WiFi 关联；
- WPA2/3 链路加密；
- 源/目的 MAC；
- 自定义 L2 载荷。

去掉：

- IPv4/IPv6；
- UDP；
- TCP；
- IP 分片；
- IP 路由/NAT。

自定义协议栈：

    H.264 视频帧
      → RTC 头
      → 分片/重组
      → FEC/NACK
      → EtherType 0x88B5
      → 802.11 QoS/WMM
      → WiFi PHY

---

## 4. 硬件方向可行性分析

| 能力 | 结论 | 证据 |
|---|---|---|
| AF_PACKET 自定义 EtherType | 可行 | 板端发送，PC Npcap 抓到 0x88B5 |
| AP→STA 自定义帧 | 可行 | 真实 5G AP 发送，PC 收到 |
| STA→AP 自定义帧 | 可行 | PC 发送，板端 l2recv 收到 |
| STA→AP→STA bridge | 可行 | AP bridge 转发 5 帧 |
| 5G H.264 视频 | 可行 | 181 帧/6.46 MB，0 丢块 |
| 2.4G H.264 视频 | 可行 | 181 帧，25 chunk 丢失 |
| 实时 30 fps | 可行 | 90 帧/3.005 s |
| FEC | 可行 | 丢 1 块恢复，SHA256 一致 |
| NACK | 可行 | 丢 seq5 重传，SHA256 一致 |
| 手机/浏览器直接参与 | 不可行 | 无 raw L2 权限 |
| 标准 WebRTC 互通 | 不可行 | 依赖 ICE/UDP |
| 跨 AP/公网/NAT | 不可行 | 无 IP 路由 |
| 每帧 CW/AIFS 动态调 | 不可行 | EDCA 是 per-AC |
| DTLS/SRTP | 未实现 | 当前 WPA2 链路加密 |

---

## 5. 技术方案

### 5.1 帧格式

    struct hdr {
      uint32_t magic;   // RTC1 = 0x52544331
      uint32_t seq;
      uint16_t len;
      uint16_t flags;   // bit0 = FEC parity
      uint32_t rsv;     // group id / timestamp
    };

以太网头 14 B + RTC 头 16 B + payload，EtherType 0x88B5。

### 5.2 发送端

- C + AF_PACKET + SOCK_RAW；
- H.264 按 AUD 分帧；
- 每帧按 1200 B 分片；
- 30 fps，每帧后 sleep 33 ms；
- FEC：8 个数据块 + 1 个 XOR parity；
- NACK：发送后缓存 3 s，收到 NACK:seq 重传；
- 可用 SO_PRIORITY 映射 WMM。

### 5.3 接收端

- Windows Npcap + Scapy；
- 过滤 EtherType 0x88B5；
- 按 seq 重组；
- FEC 恢复单块丢失；
- NACK 请求重传；
- 写 H.264；
- ffmpeg 解码验证。

### 5.4 OpenWrt 侧

- AP 端点：绑定 phy0.1-ap0；
- 两 STA 经 AP bridge：自定义 EtherType 走 Linux bridge；
- 关闭 client isolation；
- 用 tcpdump/Npcap 验证无 IP/UDP；
- raw socket 需要 root。

### 5.5 TODO

- jitter buffer；
- 实时播放器；
- 简化 GCC；
- DTLS/SRTP 或 AES-GCM；
- 多流/多 STA 公平性；
- SparkRTC 媒体层可选接入。

---

## 6. 实验方法

### 6.1 拓扑 A：AP 端点

    BPI-R4 5G AP --WiFi--> PC WLAN3

- AP 发送；
- PC 接收；
- 管理走以太网。

### 6.2 拓扑 B：两 STA 经 AP bridge

    PC WLAN3 --WiFi--> BPI-R4 AP bridge --WiFi--> PC 自带 WLAN

- 两个独立 WiFi 网卡；
- AP 只做 L2 bridge。

### 6.3 测试项

1. 最小 H.264 文件传输；
2. 实时 30 fps 帧级传输；
3. 双向 PC→AP + ACK；
4. 两 STA bridge；
5. FEC 丢块恢复；
6. NACK 丢块重传；
7. 真实摄像头 5G/2.4G/背景负载；
8. UDP/IP 基线对比。

### 6.4 判定

- 接收端能否重组；
- ffmpeg 能否解码；
- chunk 丢失数；
- SHA256 是否一致；
- 抓包是否只有 0x88B5、无 IP/UDP。

---

## 7. 原始测试数据

### 7.1 最小视频传输

发送：

    /root/l2video_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test.h264 1200
    sent 64 chunks, iface=phy0.1-ap0

接收：

    chunks 64 max 63
    missing 0 bytes 76456

解码：

    frame= 90 fps=0.0 q=-0.0 Lsize=N/A time=00:00:03.00

### 7.2 实时 30 fps

发送：

    sent 90 frames 97 chunks in 3005 ms fps=30

接收：

    chunks 97 max 96 span 2.97
    missing 0 bytes 69414

解码：

    frame= 90 fps=0.0 q=-0.0 Lsize=N/A time=00:00:03.00

### 7.3 双向 PC→AP

板端：

    listening iface=phy0.1-ap0 ack=1
    rx src=90:de:80:1c:6a:7a len=10 payload=PC_TO_AP_0
    rx ... PC_TO_AP_1
    rx ... PC_TO_AP_2
    rx ... PC_TO_AP_3
    rx ... PC_TO_AP_4

PC 收到：

    ACK 36:19:86:e0:2e:0f > 90:de:80:1c:6a:7a (0x88b5) / Raw
    ... 共 5 个

### 7.4 两 STA 经 AP bridge

    90:de:80:1c:6a:7a > c0:35:32:19:cc:fb (0x88b5) / Raw
    b'BRIDGE_TEST_0'
    b'BRIDGE_TEST_1'
    b'BRIDGE_TEST_2'
    b'BRIDGE_TEST_3'
    b'BRIDGE_TEST_4'

5 帧全部转发。

### 7.5 FEC

发送：

    /root/l2fec_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264
    fec sent groups=8 frames=66

接收（故意丢 seq=5）：

    deliberately dropped seq 5
    data 57 parity 8
    recovered 5 len 1200
    bytes 69414 missing 7 sha da4222b1b9a654fd

SHA256：

    DA4222B1B9A654FD57A90D734D743072FEB3755E397F2CB9F0704543C0740D94
    DA4222B1B9A654FD57A90D734D743072FEB3755E397F2CB9F0704543C0740D94

说明：missing 7 是 parity 帧序号不参与数据拼接，不是 7 个数据块丢失。

### 7.6 NACK

发送：

    sent 58 chunks, waiting NACK 3s
    NACK 5 -> resend
    done resent=2

接收：

    drop seq5, send NACK
    got retransmit seq5
    chunks 58 nack True max 57
    bytes 69414 missing 0 sha da4222b1b9a654fd

SHA256 完全一致。

### 7.7 真实摄像头

摄像头：Integrated Camera 640x480 @30fps，H.264 约 8 Mbit/s。

| 场景 | chunk | 丢失 | 接收字节 | 接收跨度 | 解码帧 |
|---|---|---|---|---|---|
| 5G 空闲 | 5754 | 0 | 6,584,449 | 6.439 s | 181 |
| 5G + 322 Mbit/s 背景 | 5011 | 0 | 5,678,619 | 6.461 s | 181 |
| 2.4G | 4979 | 25 | 5,650,042 | 6.494 s | 181 |

### 7.8 UDP/IP 基线 vs RT-L2（18 次）

| 场景 | 次数 | 方法 | chunk | 丢失 | 字节 | 帧数 |
|---|---|---|---|---|---|---|
| 5G_IDLE | 1 | UDP/IP | 4993 | 0 | 5,895,282 | 164 |
| 5G_IDLE | 1 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 5G_IDLE | 2 | UDP/IP | 4975 | 0 | 5,874,432 | 163 |
| 5G_IDLE | 2 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 5G_IDLE | 3 | UDP/IP | 4993 | 0 | 5,895,282 | 164 |
| 5G_IDLE | 3 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 5G_LOAD | 1 | UDP/IP | 4938 | 0 | 5,831,096 | 162 |
| 5G_LOAD | 1 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 5G_LOAD | 2 | UDP/IP | 4975 | 0 | 5,874,432 | 163 |
| 5G_LOAD | 2 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 5G_LOAD | 3 | UDP/IP | 4938 | 0 | 5,831,096 | 162 |
| 5G_LOAD | 3 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 2G4 | 1 | UDP/IP | 4975 | 0 | 5,874,432 | 163 |
| 2G4 | 1 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 2G4 | 2 | UDP/IP | 4975 | 0 | 5,874,432 | 163 |
| 2G4 | 2 | RT-L2 | 5471 | 0 | 6,459,658 | 181 |
| 2G4 | 3 | UDP/IP | 4920 | 0 | 5,810,091 | 161 |
| 2G4 | 3 | RT-L2 | 5467 | 4 | 6,455,787 | 181 |

说明：

- UDP 的 missing=0 只表示已收到的 seq 无空洞；其 max seq 小于 5471，实际是尾部整段丢失；
- RT-L2 在 5G 两场景 3/3 完整；
- 2.4G 一次丢 4 块，但 181 帧仍可解码；
- 原始 CSV：matrix_raw.csv。

---

## 8. 结果分析

### 8.1 可行性

- 自定义 EtherType 在真实 WiFi 上可收发；
- AP bridge 可转发；
- H.264 可完整传输；
- 实时 30 fps 可做到；
- FEC/NACK 可恢复丢块；
- 无 IP/UDP。

### 8.2 硬件限制

- raw socket 需要 root；
- 手机/浏览器无 raw L2 权限；
- 没有 IP 路由/NAT，跨 AP/公网不可行；
- 802.11 只有 4 个 AC，不能每帧改 CW/AIFS；
- MT7996 固件控制聚合/重传，驱动不能任意 per-frame 调度；
- 当前仅 WPA2 链路加密，没有 DTLS/SRTP。

### 8.3 与标准 WebRTC

- 标准 WebRTC 依赖 ICE/UDP/DTLS/SRTP；
- 本方案是自定义 L2 RTC，不是标准 WebRTC；
- 不能与浏览器/手机 App 直接互通；
- 需要两端都实现自定义协议。

---

## 9. 原始文件与复现

    _work_final/rtc_over_wifi/
      l2video_send_rt.c
      l2video_recv_rt.py
      l2fec_send.c
      l2fec_recv.py
      l2nack_send.c
      l2nack_recv.py
      l2send.c
      l2recv.c
      live_cam_send.py
      live_cam_recv.py
      test.h264
      test_aud.h264
      matrix_raw.csv
      recv_rt_first.png
      recv_live_first.jpg
      videos/
      implementation_report.md
      full_test_results.md
      real_world_test.md
      comparison_results.md

复现命令示例：

    /root/l2video_send_rt phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264 30

    python _work_recover/l2video_recv_rt.py

    /root/l2fec_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264

    /root/l2nack_send phy0.1-ap0 90:de:80:1c:6a:7a /root/test_aud.h264

---

## 10. 结论与建议

### 已完成

- 硬件可行性验证；
- 自定义 EtherType L2 视频；
- 实时 30 fps；
- 双向 ACK；
- 两 STA bridge；
- FEC/NACK；
- 真实摄像头 5G/2.4G；
- UDP/IP 基线对比。

### 未完成

- 实时播放器/jitter buffer；
- 自适应拥塞控制；
- DTLS/SRTP；
- 多流/多 STA 公平性；
- 手机/浏览器端点。

### 建议

1. 若目标是边缘专用视频链路：继续做 jitter buffer、CC、安全；
2. 若要求浏览器/手机：放弃 raw L2，改用标准 WebRTC + IP/QoS；
3. 若要求“完整 WebRTC over L2”：需要重写 ICE/DTLS/SRTP transport，工作量大；
4. 不要承诺每帧 CW/AIFS 或零延迟抢占，商品 MT7996 做不到。

---

## 11. 一句话总结

边缘单 L2 域、自定义 Linux/OpenWrt 端点、H.264 视频传输：**技术可行，已完成初步验证**；标准 WebRTC/手机/浏览器/跨公网：**不可行**。
