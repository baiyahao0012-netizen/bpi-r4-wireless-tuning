# RTC over WiFi 真实场景测试（2026-10-26）

## 1. 为什么是真实场景

不是文件回放，而是：

- Windows 集成摄像头实时采集 640x480 @30fps；
- H.264 编码后直接通过自定义 EtherType 0x88B5 发送；
- 发送 STA：PC WLAN3；
- 接收 STA：PC 自带 WLAN；
- 中间经过 BPI-R4 AP bridge；
- 没有 IP/UDP；
- 分别测试 5G、2.4G、5G+背景负载。

## 2. 拓扑

    Integrated Camera
      → ffmpeg libx264 (AUD/zerolatency)
      → Scapy AF_PACKET/Npcap send on WLAN3
      → BPI-R4 AP bridge
      → WLAN (Realtek 8852CE) receive
      → H.264 重组 → ffmpeg 解码

## 3. 测试结果

| 场景 | chunk | 丢失 | 接收字节 | 接收跨度 | 解码帧 |
|---|---|---|---|---|---|
| 5G 空闲 | 5754 | 0 | 6,584,449 | 6.439 s | 181 |
| 5G + 322 Mbit/s 背景 | 5011 | 0 | 5,678,619 | 6.461 s | 181 |
| 2.4G | 4979 | 25 | 5,650,042 | 6.494 s | 181 |

说明：

- 摄像头实际约 6 s；解码 181 帧约等于 30 fps；
- 5G 空闲/背景负载下 0 丢包；
- 2.4G 下 25 个 chunk 丢失（约 0.5%），但仍解码 181 帧，画面可出但有丢块/花屏风险；
- 这正是 FEC/NACK 要解决的问题。

## 4. 真实场景结论

1. 5G HE80 下，实时摄像头 8 Mbit/s 级视频通过 AP bridge 两个 STA 传输，0 丢包；
2. 加入 322 Mbit/s 背景流仍 0 丢包，说明 5G 空口余量足够；
3. 2.4G 下出现约 0.5% chunk 丢失，视频仍能解码，但需要 FEC/NACK；
4. 这套链路不是“实验室文件传输”，而是实际摄像头→编码→L2→AP bridge→解码。

## 5. 与最终方案的关系

最终 v1 线路包含：

- 实时 30 fps 帧级 pacing；
- XOR FEC；
- NACK 缓存重传；
- EtherType 0x88B5；
- AP bridge / AP 端点；
- WPA2。

真实测试说明：

- 5G 高容量下 FEC/NACK 是余量；
- 2.4G/弱网下 FEC/NACK 是必需；
- 固定 30 fps 对 8 Mbit/s 摄像头够用，暂不需要自适应 CC。

## 6. 复现文件

- live_cam_send.py
- live_cam_recv.py
- recv_live.h264（2.4G 接收样本）
- recv_live_first.jpg
