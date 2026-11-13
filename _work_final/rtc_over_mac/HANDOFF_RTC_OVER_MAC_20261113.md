# RTC over MAC 阶段总结与交接文档

日期：2026-11-13  
交接对象：下一个执行 Agent  
仓库路径：`_work_final/rtc_over_mac/`

## 0. 仓库与阅读入口

- **远程仓库**：<https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning.git>
- **本地路径**：`D:\Desktop\AI 辅助对话`
- **分支**：`main`
- **本交接提交**：`c2acca1 docs: add RTC over MAC handoff and baseline evidence`
- **本项目主目录**：`_work_final/rtc_over_mac/`
- **测试素材目录**：`_work_final/rtc/media/testset_1080p/`（六条 1080p 原始视频与 MANIFEST）

仓库整体内容：该仓库用于 BPI-R4 无线调优与 RTC over MAC 研究。  
`rtc_over_mac/` 下包含本项目的方案、L0/UDP baseline 报告、L2 原型、测试脚本、诊断记录和本交接文档；  
`rtc_over_wifi/` 是更早的 RTC 功能审计材料；  
`rtc/media/testset_1080p/` 是六条 1080p 测试视频及元数据。

阅读顺序建议：

```text
HANDOFF_RTC_OVER_MAC_20261113.md   ← 先读本文件
REVISED_PLAN_20261112.md           ← 方案与阶段划分
L1_BASELINE_SIX_20261112.md        ← 六片 UDP baseline
L2_PROTOTYPE_20261112.md           ← L2 原型与可靠性实验
L1_RECEIVER_DIAG_20261112.md       ← 接收端诊断与修正
t7_sender.sh / t7_receiver.sh      ← T7 反馈实验脚本
```

## 1. 项目目标

本项目只做 **RTC 媒体面**，不做完整 WebRTC。目标是：

```text
标准 RTP/RTCP/SRTP 媒体层
  ├─ A. UDP/IP baseline（对照组）
  └─ B. RTC over MAC（本轮目标）
        RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC
        去掉 UDP/IP，但保留 RTC 层
```

C 形态（RTC 层消失、帧直接进 MAC 调度器）是后续目标，不在本轮范围。

## 2. 已搭建场景

```text
树莓派 5（STA）
  ├─ eth0 192.168.240.153：管理
  └─ wlan1 192.168.240.126：媒体，USB MT7921AU
          │ 802.11 5G，ch149，80 MHz
          ▼
BPI-R4 AP（OpenWrt，192.168.240.1，仅 bridge）
          │ 有线 Ethernet
          ▼
Windows 笔记本（算力平台，192.168.240.2）
  接收 + 解码 + 后续处理
```

关键决定：

- 板载 `wlan0`（brcmfmac）禁用并设为 NetworkManager unmanaged；
- 媒体统一走 USB `wlan1`，避免双 Wi-Fi 竞争、默认路由/扫描干扰；
- 管理走 `eth0`，媒体走 `wlan1`，避免 SSH 与媒体抢空口；
- AP 只做 bridge，不运行媒体栈；
- Pi 策略路由：`from 192.168.240.126 lookup 100`，table 100 指向 `wlan1`；  
  该路由**重启后会丢失**，每次测试前用 `ip route get <目标IP> from 192.168.240.126` 复核。

## 3. 技术思路

1. 用 GStreamer 1.26.x 作为开源媒体层（Pi 1.26.2，Windows 1.26.11）；
2. 用用户提供的六条 1080p 原始视频，完整时长，不派生 10/15/20 Mbps；
3. 先在 UDP/IP 上做完整媒体层验证，冻结 baseline；
4. 再做 L2 shim（EtherType `0x88B5`，12B 头 + CRC），去掉 UDP/IP；
5. 对未受影响功能做回归，对受影响功能打补丁；
6. 最终验收 B 形态。

## 4. 已完成进展

### 4.1 UDP baseline（已冻结 v1）

| 素材 | 源帧 | 解码 | 完整率 |
|---|---:|---:|---:|
| 1080p24_1 | 1253 | 1251 | 99.840% |
| 1080p24_2 | 2161 | 2160 | 99.954% |
| 1080p25_3 | 812 | 811 | 99.877% |
| 1080p30_1 | 2560 | 2558 | 99.922% |
| 1080p30_2 | 2273 | 2271 | 99.912% |
| 1080p30_3 | 2702 | 2700 | 99.926% |
| **合计** | **11761** | **11751** | **99.915%** |

每片差 1–2 帧，集中在尾部，属无 EOS 末帧滞留；作为 L2 对比基线足够，严格 11761/11761 未完成。

相关文件：

- `L1_BASELINE_SIX_20261112.md`
- `fullset_baseline.csv`
- `L1_BASELINE_FULL_20261112.md`

### 4.2 T3/T4（已闭环）

- T3：`302/302`；
- T4：SRTP `302/302`，`recv-count=5933`，`recv-drop-count=0`；
- 关键修复：接收端 `udpsrc buffer-size=8MB` + 发送结束后向接收 pipeline 注入 EOS。

相关脚本（Pi）：

```text
/home/bai/rtc_test/t3_eos_receiver.py
/home/bai/rtc_test/l0/srtp_loopback_eos.py
```

### 4.3 T7 反馈机制（部分完成）

采用 GStreamer 官方组合：

```text
rtpsession rtp-profile=avpf
+ rtprtxsend / rtprtxreceive
+ rtpjitterbuffer do-retransmission=true do-lost=true
+ rtph264depay request-keyframe=true
+ identity drop-probability=0.05
```

当前结果：

```text
5% 丢包：292 / 302 帧 = 96.7%
```

之前最小回环为 136/302；干净启动后提升明显。  
已确认 NACK/RTX 真实发生（`rtx-count` / `recv-rtx-req-count` 增长），但：

- 仍差 10 帧；
- `sent-pli-count` 未确认非零；
- 文件源无法现场产生新 IDR，PLI 恢复需实时编码器；
- 尚未接出 `rtprtxreceive/rtprtxsend/rtpjitterbuffer` 全量计数器，10 帧缺口未归因。

相关脚本：

- `t7_sender.sh`
- `t7_receiver.sh`

注意：`pkill -f t7_receiver.sh` 会匹配 SSH 命令行自身；应使用 `pkill -f "[t]7_receiver.sh"`，且不要把 `rtpsession` 关键字和 `pkill` 放在同一远程命令行中。

### 4.4 T8（未开始）

需要：

```text
rtpbin 视频/音频双 session
音频 jitterbuffer
RTCP SR 的 NTP↔RTP
PC/Pi 时钟偏移
锚点素材 A/V skew
```

当前 20ms 是“去 jb”的本地基准，不是 rtpbin 闭环结果。

### 4.5 L2 原型（部分完成）

- `0x88B5` 双向通过；
- AP bridge 不丢自定义 EtherType；
- 12B shim + CRC；
- 接收端已去掉本地 UDP：L2 → shim → RTP → 回绕感知重排 → H.264 → PyAV；
- 30_1 完整片：**2556/2560（99.84%）**，UDP baseline 2558/2560，差 2 帧；
- 24_2（7 Mbps）：**774/2161（35.8%）**，高码率不可用；
- 1+1 双发：1743/2161（80.6%）；三发：740/2161（34.2%）；pacing：772/2161（35.7%）；
- 结论：盲重复/三发/pacing 无效，必须做 NACK/FEC；正式 `l2sink/l2src` 未实现，Pi 发送端仍有本地 UDP 胶水。

相关文件：

- `L2_PROTOTYPE_20261112.md`
- `l2_rtp_send.py`
- `l2_rtp_decode_reorder.py`
- `l2_probe_send.py` / `l2_probe_recv.py`

## 5. 关键未完成项

1. T7 的 10 帧缺口归因；
2. T7 PLI 206 出站；
3. T8 rtpbin 双流 + 音频 jb + 时钟；
4. 正式 `l2sink/l2src`；
5. L2 高码率 NACK/FEC；
6. 六片 L2 矩阵、影响矩阵、补丁、B 验收；
7. 跨机时钟（PC `w32time` 当前状态需现场复核）。

## 6. 给下一个 Agent 的执行顺序

```text
1. 复核网络/路由/时钟
2. T7：干净启动 + RTX/jb 计数器接出
3. T7：0.1% 丢包验关联/缓存，5% 丢包分离 RTX 与 PLI
4. T7：PLI 206 出站；需要恢复则接实时编码器
5. T8：rtpbin 双 session + 音频 jb + RTCP SR + 时钟
6. 正式 l2sink/l2src
7. L2 NACK/FEC，先打 24_2
8. 六片 L2 + 影响矩阵 + 补丁 + B 验收
```

## 7. 当前结论

- UDP baseline 已冻结；
- T3/T4 已闭环；
- T7 有实质进展但未验收；
- T8 未开始；
- L2 低码率接近 baseline，高码率可靠性失败；
- B 形态未完成。

本文件为交接基线，不把未验证项写成已完成。
