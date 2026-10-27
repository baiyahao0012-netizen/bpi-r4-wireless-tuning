# RTC over WiFi 发射端/接收端视频

## 目录

    videos/
      sender/
        sender_camera_30fps.mp4
        sender_camera_30fps.h264
      receiver/
        receiver_l2_5g_30fps.mp4
        receiver_l2_5g_30fps.h264
        receiver_l2_2g4_live.mp4
        receiver_l2_2g4_live.h264
        receiver_udp_5g_30fps.mp4
        receiver_udp_5g_30fps.h264

## 测试条件

- 摄像头：Windows Integrated Camera，640x480 @30fps；
- 编码：H.264，AUD，zerolatency；
- 时长：约 6 s，181 帧；
- 发送：BPI-R4 5G AP；
- 接收：PC WLAN3；
- 自定义 EtherType 0x88B5；
- 无 IP/UDP。

## 文件说明

### sender/

- sender_camera_30fps.h264：发射端摄像头原始采集；
- sender_camera_30fps.mp4：同一内容的 MP4 封装，方便播放。

### receiver/

- receiver_l2_5g_30fps：5G 下 RT-L2 接收；
  - 5471 chunk；
  - missing 0；
  - 6,459,658 B；
  - 181 帧；
  - SHA256 与发送端完全一致。
- receiver_l2_2g4_live：2.4G 下真实直播接收；
  - 4979 chunk；
  - missing 25；
  - 181 帧仍可解码；
  - 用于观察 2.4G 丢块/花屏。
- receiver_udp_5g_30fps：UDP/IP 基线接收样本；
  - 本次样本 5471 chunk、0 缺失、181 帧；
  - 注意：多次矩阵测试中 UDP 常出现尾部缺失（见 comparison_results.md）。

## SHA256

发送端与 5G L2 接收端 H.264 完全一致：

    8202AAE460BE6F16DB8CFA38F89A0D99B92EFD31A9FAB4130F538566F04F2A61

2.4G 样本因 25 个 chunk 丢失，SHA 不同，但仍解码 181 帧。

## 播放

直接双击 MP4：

- sender_camera_30fps.mp4
- receiver_l2_5g_30fps.mp4
- receiver_l2_2g4_live.mp4
- receiver_udp_5g_30fps.mp4

H.264 文件供 ffmpeg/分析工具使用。

## 对应报告

- ../implementation_report.md
- ../comparison_results.md
- ../real_world_test.md
