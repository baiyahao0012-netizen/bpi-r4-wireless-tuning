# RTC over WiFi（去掉 UDP/IP）可行性分析与本周方案

目标：在 OpenWrt/BPI-R4 边缘场景中，验证 WebRTC 视频能否绕过 UDP/IP，直接用 802.11 L2 自定义帧传输。
参考：https://github.com/hkust-spark/sparkrtc

## 1. 结论先行

在“单一 802.11 L2 域 + 两端可控 Linux/OpenWrt 设备”的边缘场景下，技术可行；
但不是标准 WebRTC，也不能直接与浏览器/手机 App 互通。

| 场景 | 可行性 |
|---|---|
| 同一 AP 下，两台 Linux/OpenWrt 设备，自定义 L2 协议 | 可行 |
| OpenWrt AP 自己作为视频发送端/接收端，一个 Linux STA | 可行，最容易做 |
| 两台 WiFi STA 经 AP 桥接自定义 EtherType | 可行，但需验证 bridge/ebtables 转发 |
| 标准浏览器 WebRTC / 手机 App 直接接收 | 不可行：浏览器/Android 无 raw L2 权限，WebRTC 依赖 ICE/UDP |
| 跨路由器/WAN/公网 | 不可行：没有 IP 就没有 NAT/路由；加隧道又会重新引入 IP/UDP |
| 完整 SparkRTC 直接跑在 L2 上 | 不可直接：SparkRTC 仍假设 UDP/IP socket，需要替换 transport |

## 2. “去掉 UDP/IP”到底去掉什么

建议把目标定义为：

应用：H.264/VP8 视频帧
RTC 层：自定义帧头 + 分片/重组 + 序列号 + FEC/NACK + 拥塞控制
L2：自定义 EtherType（如 0x88B5）
MAC：802.11 QoS data frame / LLC-SNAP
PHY：WiFi

即：保留 802.11 MAC/LLC 和 WiFi 关联/加密，去掉 IPv4/IPv6、UDP、TCP。

仍然需要：

- WiFi 关联、WPA2/3 加密；
- 源/目的 MAC 地址；
- 应用层分片/重组（不能依赖 IP fragmentation）；
- 自定义拥塞控制/丢包恢复（不能依赖 UDP/TCP）。

## 3. WebRTC 各层能否保留

| WebRTC 层 | 去掉 IP/UDP 后 |
|---|---|
| ICE/STUN/TURN | 不能直接用：依赖 UDP/IP 和候选地址；单 AP 场景可替换为固定 MAC/AP 发现 |
| DTLS | 可跑在自定义 datagram 上，但需要重写传输适配 |
| SRTP | 可跑在自定义 datagram 上 |
| RTP/RTCP | 可自定义封装，但 RTCP 反馈要自己实现 |
| GCC/拥塞控制 | 需要改反馈通道；可参考 SparkRTC 的 GCC/FEC |
| 视频 codec/抖动缓冲/FEC | 可复用 SparkRTC/WebRTC 的媒体层 |

结论：媒体层可复用，传输层必须重写。

## 4. 推荐架构

Sender (Linux/OpenWrt)                 Receiver (Linux/OpenWrt)
  H.264 frames                          ffplay / GStreamer
  RTC header/fragment/FEC               reassembly/jitter buffer
  AF_PACKET + EtherType 0x88B5   <-->    AF_PACKET
  802.11 STA/AP                         802.11 STA/AP
                  \                       /
                   \---- BPI-R4 AP -----/

### 4.1 帧格式（最小版）

struct rtc_l2_hdr {
  uint32_t magic;       // RTC1
  uint8_t  version;
  uint8_t  type;        // video/audio/feedback
  uint16_t stream_id;
  uint32_t seq;
  uint32_t frame_id;
  uint16_t frag_idx;
  uint16_t frag_count;
  uint64_t ts_us;
  uint16_t payload_len;
  uint32_t crc32;
};

- EtherType 建议用实验值 0x88B5；
- 每帧 H.264 按 1200-1400 B 分片；
- 接收端按 frame_id/frag_idx 重组；
- 先不做 FEC，跑通后再加 XOR/RS。

### 4.2 OpenWrt 侧

- AF_PACKET raw socket 需要 root；OpenWrt 默认 root，可行；
- 若 AP 是端点：绑定 phy0.1-ap0 或 br-lan；
- 若两个 STA 经 AP 转发：自定义 EtherType 走 Linux bridge，需要确认 ebtables/nft bridge 不丢未知 EtherType；
- 关闭 AP client isolation；
- 用 tcpdump -e ether proto 0x88b5 验证没有 IP/UDP；
- QoS：raw socket SO_PRIORITY=256+5/6 映射到 802.11 VI/VO；
- MTU 1500，应用层分片。

## 5. 最小 Demo（本周目标）

拓扑 A（最容易）：OpenWrt AP（发送端） --WiFi--> Linux PC（接收端）。
AP 直接 AF_PACKET 发自定义帧到 STA 的 MAC，不需要 bridge 转发。

拓扑 B（更接近客户端到客户端）：Linux PC A --WiFi--> BPI-R4 AP --WiFi--> Linux PC B。
需要 AP bridge 转发自定义 EtherType。

步骤：

1. l2rtc_send：读 H.264 Annex-B 文件，分片，AF_PACKET 发送；
2. l2rtc_recv：AF_PACKET 收包，重组，写 FIFO；
3. ffplay -f h264 fifo 显示；
4. tcpdump -e 确认 EtherType 0x88B5、无 IP/UDP；
5. 先 720p，再 1080p；先文件，后摄像头/GStreamer。

验收：

- 接收端能正常播放视频；
- 无 IP/UDP 包；
- 记录 FPS、丢帧、端到端时延（发送时间戳 vs 显示时间）。

## 6. SparkRTC 怎么用

SparkRTC 是基于 WebRTC 的超低延迟实现，但仍假设 UDP/IP socket。可复用：

- GCC/带宽估计；
- FEC/抖动缓冲；
- 视频 pipeline/编码。

但需要把 UDP socket / ICE transport 替换成自定义 L2 transport；这不是改一个 socket 类型，而是重写 transport/ICE 层，工作量大。

建议：先用轻量自定义 sender/receiver 跑通 L2 视频，再评估是否把 SparkRTC 的媒体层接进来。

## 7. 为什么“标准 WebRTC/手机”不行

1. 浏览器 WebRTC API 只暴露 IP/UDP/ICE，不能发 raw 802.11 帧；
2. Android/iOS App 无 raw L2 权限（VPNService 只到 IP 层）；
3. 没有 IP 就没有 NAT/路由，跨 AP/公网不可达；
4. 需要两端都实现自定义协议，不能与普通 WebRTC 端点互通；
5. DTLS/SRTP/RTCP 需要额外适配；
6. 802.11 重传/聚合/速率控制会改变时延特性，需要重新做拥塞控制。

## 8. 本周 TODO

- [ ] 定义 EtherType/帧头/分片格式；
- [ ] 写 l2rtc_send / l2rtc_recv（C + AF_PACKET）；
- [ ] OpenWrt AP 端点模式跑通 720p H.264；
- [ ] 两 STA 经 AP bridge 模式跑通；
- [ ] tcpdump 证明无 IP/UDP；
- [ ] 记录 FPS/丢帧/时延；
- [ ] 评估 SparkRTC transport 替换工作量，写结论。

## 9. 风险

- raw socket 权限：仅 root/Linux/OpenWrt；
- bridge/ebtables 可能过滤自定义 EtherType；
- 802.11 加密/关联由驱动处理，自定义帧仍受 WMM/聚合影响；
- 没有 IP 分片，应用分片/重组必须正确；
- 浏览器/手机无法直接参与，演示必须用 Linux/OpenWrt 端点；
- “完整 WebRTC over L2”是研究原型，不是生产方案。
