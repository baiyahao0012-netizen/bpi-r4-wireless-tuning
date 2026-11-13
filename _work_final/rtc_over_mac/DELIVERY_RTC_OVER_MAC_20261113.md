# RTC over MAC 总交付文档

日期：2026-11-13  
交付对象：下一个接手的 Agent  
文档定位：**先读这一份，再按文件地图进入细节。**

---

## 0. 仓库、地址与阅读入口

- **GitHub 仓库**：<https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning.git>
- **本地仓库**：`D:\Desktop\AI 辅助对话`
- **分支**：`main`
- **本项目主目录**：`_work_final/rtc_over_mac/`
- **测试素材**：`_work_final/rtc/media/testset_1080p/`
- **Windows 接收端 GStreamer**：`C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64\bin`

### 要先理解的仓库背景

这个仓库不是单纯的 RTC 项目，而是 **BPI-R4 无线调优 + RTC over MAC 研究** 的仓库：

- `_work_final/rtc_over_mac/`：当前 RTC over MAC 的主工作区；
- `_work_final/rtc_over_wifi/`：更早的 RTC 功能审计材料（HTML/截图等）；
- `_work_final/rtc/media/testset_1080p/`：六条 1080p 测试视频、锚点素材、MANIFEST；
- 旧 RTC2 是 Windows 私有协议的历史材料，**不作为当前 Pi 的“旧媒体层”**；
- 当前 Pi 是全新环境，媒体层是从 GStreamer 开始搭的。

建议阅读顺序：

```text
DELIVERY_RTC_OVER_MAC_20261113.md   ← 本文件
REVISED_PLAN_20261112.md            ← 方案/阶段
L1_BASELINE_SIX_20261112.md         ← 六片 UDP baseline
L2_PROTOTYPE_20261112.md            ← L2 结果与可靠性实验
L1_RECEIVER_DIAG_20261112.md        ← 接收端诊断
HANDOFF_RTC_OVER_MAC_20261113.md    ← 简明交接
```

---

## 1. 当前目标

只做 **RTC 媒体面**，不做完整 WebRTC。

三个形态必须分清：

```text
A. UDP baseline
   RTP/RTCP/SRTP → UDP/IP → Wi-Fi MAC

B. RTC over MAC（本轮目标）
   RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC
   去掉 UDP/IP，但保留 RTC 层

C. MAC-native（后续）
   视频帧/Token → MAC 调度器
   RTC 层消失
```

当前目标是 **B**，不是 C。  
本轮只验证“去掉 UDP/IP”后的媒体层功能、性能和受影响功能，不承诺 RTC 层消失。

---

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

### 关键选择及原因

1. **禁用板载 wlan0**
   - 板载 `brcmfmac` 与 USB `wlan1` 同时在线会造成双 Wi-Fi 竞争、扫描/默认路由干扰；
   - 禁用并设为 NetworkManager unmanaged，媒体只走 `wlan1`。

2. **使用 USB wlan1（MT7921AU）**
   - 5G、80 MHz，便于固定信道和参数；
   - 接口唯一，便于固定源地址、路由和计数器归因；
   - 管理走 `eth0`，媒体走 `wlan1`，避免 SSH 抢空口。

3. **AP 只做 bridge**
   - AP 不跑媒体栈、不解码；
   - 接收端和算力都在笔记本；
   - AP 只负责无线接入和 L2 转发。

4. **Pi 策略路由**
   - `ip rule: from 192.168.240.126 lookup 100`
   - `table 100: 192.168.240.0/24 dev wlan1`
   - 该路由是运行时配置，**重启后会丢失**；
   - 每次测试前必须：
     ```bash
     ip route get <目标IP> from 192.168.240.126
     ```
     出口必须是 `dev wlan1`。

---

## 3. 技术思路

1. 使用 GStreamer 作为开源媒体层：
   - Pi：GStreamer 1.26.2；
   - Windows：GStreamer 1.26.11；
   - 只用标准元件：`rtpbin`、`rtpjitterbuffer`、`rtph264pay/depay`、`rtpopuspay/depay`、`srtpenc/srtpdec`、`rtprtxsend/receive`。

2. 用用户提供的六条 1080p 视频：
   - 完整时长；
   - 不派生 10/15/20 Mbps；
   - 视频-only baseline，音频后加。

3. 先 UDP/IP，后 L2：
   - UDP baseline 冻结后再做 L2；
   - 同一素材、同一接收端、同一指标对比。

4. 受影响功能打补丁，未受影响功能回归。

---

## 4. 当前进展

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

- 每片发送端 `rc=0`；
- 无 GStreamer 致命错误；
- 每片差 1–2 帧，集中在尾部；
- 作为 L2 对比基线冻结，严格 11761/11761 仍未完成。

### 4.2 T3/T4（已闭环）

```text
T3：302/302
T4：SRTP 302/302
    recv-count=5933
    recv-drop-count=0
```

关键修复：

- 接收端 `udpsrc buffer-size=8MB`；
- 发送结束后向接收 pipeline 注入 EOS，冲刷 `avdec_h264` 尾部。

### 4.3 T7 反馈机制（部分完成）

采用官方组合：

```text
rtpsession rtp-profile=avpf
+ rtprtxsend / rtprtxreceive
+ rtpjitterbuffer do-retransmission=true do-lost=true latency=500
+ rtph264depay request-keyframe=true
+ identity drop-probability=0.05
```

结果：

```text
5% 丢包：292 / 302 = 96.7%
```

之前最小回环为 136/302。  
NACK/RTX 已真实发生（`rtx-count` 增长），但：

- 仍差 10 帧；
- `sent-pli-count` 未确认非零；
- 文件源不能现场产生新 IDR；
- 10 帧缺口尚未用计数器归因。

### 4.4 T8（未开始）

T8 需要：

```text
rtpbin 视频/音频双 session
音频 jitterbuffer
RTCP SR 的 NTP↔RTP
PC/Pi 时钟偏移
锚点 A/V skew
```

当前 20ms 是“去 jb”的本地基准，不是 rtpbin 闭环结果。

### 4.5 L2 原型（部分完成）

- `0x88B5` 双向通过；
- AP bridge 不丢自定义 EtherType；
- 12B shim + CRC；
- 接收端已去掉本地 UDP：
  ```text
  L2 → shim → RTP → 回绕感知重排 → H.264 → PyAV
  ```

结果：

| 测试 | 结果 |
|---|---|
| 10 s | 6809/6809 包，0 CRC，301/302 帧 |
| 30_1 完整片 | **2556/2560 = 99.84%** |
| UDP baseline 同片 | 2558/2560 |
| 24_2 高码率 | **774/2161 = 35.8%** |
| 24_2 1+1 双发 | 1743/2161 = 80.6% |
| 24_2 三发 | 740/2161 = 34.2% |
| 24_2 pacing | 772/2161 = 35.7% |

结论：

- 低码率 L2 已接近 UDP baseline；
- 高码率 7 Mbps 下，盲重复/三发/pacing 都无效；
- 必须做选择性 NACK/重传或 FEC；
- 正式 `l2sink/l2src` 尚未实现；Pi 发送端仍有本地 UDP 胶水。

---

## 5. 代码地图与用途

### T3/T4

| 文件 | 用途 |
|---|---|
| `t3_eos_receiver.py` | T3 显式 EOS 接收端，302/302 |
| `srtp_loopback_eos.py` | T4 SRTP 双管线 + EOS + 8MB UDP 缓冲，302/302 |
| `test_harness/l0_verify/srtp_setup.sh` | 免 sudo 解包 PyGI typelib |
| `test_harness/l0_verify/srtp_run.sh` | 设置 `GI_TYPELIB_PATH` 后运行 |

### T7

| 文件 | 用途 |
|---|---|
| `t7_sender.sh` | `rtpsession + rtprtxsend + 5% loss` 发送端 |
| `t7_receiver.sh` | `rtpsession + rtprtxreceive + jb do-retransmission` 接收端 |

注意：

- `pkill -f t7_receiver.sh` 会匹配 SSH 命令行自身；
- 用 `pkill -f "[t]7_receiver.sh"`；
- 不要把 `rtpsession` 关键字和 `pkill` 放同一条远程命令行；
- 接收端启动失败时先检查 5000/5001/5002 端口和旧进程。

### L2

| 文件 | 用途 |
|---|---|
| `l2_rtp_send.py` | 本地 UDP RTP → 12B shim → `wlan1` AF_PACKET |
| `l2_rtp_decode.py` | L2 → RTP → H.264 → PyAV，无本地 UDP |
| `l2_rtp_decode_reorder.py` | 回绕感知 seq 重排后再解码 |
| `l2_probe_send.py` | Pi 最小 `0x88B5` 帧发送 |
| `l2_probe_recv.py` | Windows Npcap 最小帧捕获 |
| `l2_rtp_recv.py` | L2 → 本地 UDP 的调试胶水（非验收路径） |
| `run_l2_file.sh` | Pi 侧单条 L2 发送 |
| `run_l2_fullset.ps1` | Windows 六片 L2 矩阵 runner |

### 工具/分析

| 文件 | 用途 |
|---|---|
| `pc_rtp_receiver.py` | Windows Python/PyAV RTP 探针，clean-path 冒烟 |
| `rtp_probe.py` | RTP 头统计 |
| `parse_ap_pcap.py` / `parse_ap2.py` | AP pcap 解析 |
| `fullset_baseline.csv` | 六片 UDP baseline 数据 |
| `run_fullset_baseline.ps1` | 六片 UDP baseline runner |
| `setup_media_route.sh` | Pi 策略路由恢复 |
| `send_testset_full.sh` | 单条全片 UDP 发送 |
| `send_pc.sh` | 10 s 冒烟发送 |

### 报告

- `L0_MEDIA_LAYER_VERIFY_REPORT_20261110.md`
- `L1_BASELINE_SIX_20261112.md`
- `L1_BASELINE_FULL_20261112.md`
- `L1_RECEIVER_DIAG_20261112.md`
- `L2_PROTOTYPE_20261112.md`
- `REVISED_PLAN_20261112.md`
- `HANDOFF_RTC_OVER_MAC_20261113.md`

---

## 6. 当前未完成项

1. T7 292/302 的 10 帧缺口归因；
2. T7 PLI 206 出站；
3. T8 `rtpbin` 双流 + 音频 jb + RTCP SR + 时钟；
4. 正式 `l2sink/l2src`；
5. L2 高码率 NACK/FEC；
6. 六片 L2 矩阵；
7. 影响矩阵、补丁、B 验收；
8. 跨机时钟（PC `w32time` 需现场复核）。

---

## 7. 环境与凭据

> 用户已明确授权把调试所需凭据交给接手 Agent。  
> 这些是实验环境凭据，不是生产凭据。

### 网络

| 设备 | 地址 | 用户 |
|---|---|---|
| Pi | `192.168.240.153` | `bai` |
| Pi 媒体口 | `192.168.240.126` | — |
| AP | `192.168.240.1` | `root` |
| Windows | `192.168.240.2` | — |

### SSH

- Pi key：`C:\Users\15732\.ssh\id_ed25519_pi_rtc`
- AP root 已配置 key 免密。
- 示例：
  ```powershell
  ssh -i "$env:USERPROFILE\.ssh\id_ed25519_pi_rtc" -o IdentitiesOnly=yes bai@192.168.240.153
  ssh root@192.168.240.1
  ```

### Pi sudo

- 早期密码：`12345678`
- 注意：该密码在调试过程中出现过被拒绝的情况；若失效，请让用户在 Pi 本地执行 `sudo -v` 或更新密码。
- 不要假设它永远有效。

### 软件

- Pi：GStreamer 1.26.2；
- Windows：GStreamer 1.26.11；
- Windows 侧 GStreamer 路径：
  ```text
  C:\gstreamer\PFiles64\gstreamer\1.0\msvc_x86_64\bin
  ```
- PyGI typelib：
  ```text
  GI_TYPELIB_PATH=/home/bai/.local/gi/usr/lib/aarch64-linux-gnu/girepository-1.0
  ```

---

## 8. 已知坑

1. **策略路由重启丢失**：每次先 `ip route get`。
2. **`pkill -f` 自匹配**：会杀掉 SSH shell；用 `[t]7...` 这种写法，且不要把关键字和 pkill 放同一命令行。
3. **GStreamer 接收端预热**：UDP 六片 baseline 需要约 10 s 预热，否则启动窗口丢帧。
4. **`udpsrc` 接收缓冲**：SRTP/T7 需要 8 MB，否则丢包。
5. **无 EOS**：UDP 不传 EOS，尾部 B 帧会滞留；T3/T4 用显式 EOS 解决。
6. **文件源不能响应 PLI 生成 IDR**：T7 的 PLI 恢复必须用实时编码器。
7. **YUV/大文件**：生成物很大，不要直接普通 git 提交；用 LFS/Release/重建。
8. **Windows 时钟**：`w32time` 可能是 Stopped/Manual；T8 前必须校准并记录 offset。

---

## 9. 给下一个 Agent 的立即执行顺序

```text
1. 复核网络、路由、SSH、GStreamer 路径
2. T7：清理旧进程 → 单独启动接收端 → 确认文件增长
3. T7：接出 rtprtxreceive/rtprtxsend/jb 计数器
4. T7：0.1% 丢包验关联/缓存；5% 丢包分离 RTX 与 PLI
5. T7：PLI 206 出站；需要恢复则接实时编码器
6. T8：rtpbin 双 session + 音频 jb + RTCP SR + 时钟
7. 正式 l2sink/l2src
8. L2 NACK/FEC，先打 24_2
9. 六片 L2 + 影响矩阵 + 补丁 + B 验收
```

## 10. 一句话交接

**UDP baseline 已冻结，T3/T4 已闭环；T7 已到 292/302 但 PLI/10 帧未闭环；T8 未开始；L2 低码率接近 baseline、高码率可靠性失败。B 形态未验收。**
