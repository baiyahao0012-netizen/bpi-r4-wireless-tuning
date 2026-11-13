# 新场景：笔记本作为接收/处理平台——任务与下一步

日期：2026-11-11  
说明：豆包分享页 `https://www.doubao.com/thread/xLrUj12m1tRQy73zk` 抓取只返回动态页面壳/空正文，未能读取对话内容；以下依据你本条消息中的新场景分析。若对话里还有码率、延迟、平台等约束，请补关键段。

> 本文中关于时钟、策略路由、探针边界、Windows SRTP 和码率阶梯的表述，已由
> [`REVISED_PLAN_20261112.md`](REVISED_PLAN_20261112.md) 修订；两处冲突时以修订计划为准。

---

## 1. 新拓扑

```text
Camera / STA（Pi 5 wlan1 .126）
        │ 802.11 5G 上行
        ▼
BPI-R4 AP（.1，br-lan，仅 bridge）
        │ 有线 Ethernet
        ▼
Windows 笔记本（以太网 .2）
  接收 + 解码 + 处理
```

- AP **不再是 RTC 端点**，只做无线接入 + L2 bridge；
- 接收端在笔记本上；
- 这与之前“AP 自己跑接收端”的 R2 方案不同，**R2 从本轮关键路径移除**；
- AP 不需要 GStreamer/Python/Pion；
- 媒体终点是笔记本，第二阶段的 L2 目的 MAC 也应是**笔记本有线网卡 MAC**，不是 AP MAC。

这不是“STA→STA”：接收端是独立的笔记本平台，不是同一台 Pi 的自环。

---

## 2. 新场景带来的变化

| 项 | 旧方案 | 新场景 |
|---|---|---|
| AP 角色 | 可能是 RTC 端点 | 只做 bridge |
| 接收端 | AP 或 AP 后有线机 | **笔记本** |
| AP 媒体栈 | 可能需要 GStreamer/Pion | **不需要** |
| 基线接收端 | 未定 | 笔记本（UDP 与 L2 共用） |
| L2 目的 MAC | 参考接收端 MAC | **笔记本以太网 MAC** |
| 主要工程风险 | AP 媒体栈 | **Windows 接收栈、防火墙、SRTP、L2 收包** |

新场景的好处：

- AP 不再承担解码/媒体栈，减少一个变量；
- UDP baseline 和 L2 target 可以用**同一台笔记本、同一接收程序**对比；
- 更接近“STA 无线上行 → AP → 边缘处理平台”的实际部署。

新场景的主要难点：

- 笔记本是 Windows，当前没有 GStreamer；
- Windows 防火墙可能拦截 UDP 5004/5006；
- GStreamer `srtpdec` 需要 `request-key` 回调，`gst-launch` 不能直接配密钥；
- L2 目标需要在笔记本上收自定义 EtherType，可能需要 Npcap 或 Linux VM。

---

## 3. L0 当前状态（不能直接冻结）

| 项 | 状态 |
|---|---|
| T1 解码 | 通过 |
| T2 RTP 头 | 通过 |
| T3 回环帧数 | 300/302，EOS 严格相等未闭环 |
| T4 SRTP | 加解密 5911/0，但解码 297/302，严格相等未闭环 |
| T5 RTCP SR | 通过 |
| T6 乱序 | 通过 |
| T7 NACK/PLI/RTX | **未闭环**：205/206=0，RTX 未回填 |
| T8 音频+A/V | 本地基准通过，但音频 jb/rtpbin 双流未闭环 |
| T9 画质 | 本地流程通过 |

结论：

- **L0 可作为“本地媒体层大部分通过”的交付；不能作为项目最终交付。**
- T3/T4 的 302/302 必须用显式 EOS 复测。
- T7 是“媒体层功能正常”的必要项；可以不等它跑 clean 视频 baseline，但**不能把“媒体层已验证”写死**，也不能把 T7 留到 L2 之后再排查。
- T8 的音频 jb 必须在音频 baseline 前闭环。

---

## 4. 笔记本接收端选型

| 方案 | UDP 视频/音频 | SRTP | L2 自定义 EtherType | 结论 |
|---|---|---|---|---|
| **Windows 原生 GStreamer** | ✅ 最快 | ⚠️ 需写小型 `request-key` 接收程序 | ⚠️ 需 Npcap + 自定义 l2src | 可先做 UDP baseline |
| **Linux VM（桥接以太网）** | ✅ | ✅ PyGI/GStreamer 可做 | ✅ AF_PACKET/l2src 可做 | **完整方案首选** |
| WSL2 | ⚠️ NAT/端口转发，非同一 Ethernet | ⚠️ 可用但网络复杂 | ❌ 不适合 raw L2 | 不推荐 |
| Pion/Go 接收器 | ✅ | ✅ | ✅ Npcap/AF_PACKET | 可移植，但代码量大 |

### 推荐

1. **如果能在笔记本上跑 Linux VM，并桥接到以太网口**：首选。  
   这样 GStreamer、PyGI/SRTP、后续 `l2src` 都在同一 Linux 环境，最容易做完整 baseline 和 L2 对比。
2. **如果暂时只用 Windows 原生**：先装 GStreamer Windows runtime，做 **UDP 视频/音频 baseline**；SRTP 和 L2 接收端另做小应用或后续迁移 VM。
3. WSL2 不作为 L2 接收端方案；UDP 也可能因 NAT/端口转发引入额外变量。

> 不管哪种方案，接收端都必须绑定笔记本**以太网 .2**，不能走 Wi-Fi；Wi-Fi 只用于上网/管理。

---

## 5. 下一步操作方案

### Step 0：L0 收口（Pi 本地，先做）

1. T3/T4：显式 EOS，做到 **302/302**；
2. T7：`request-jitterbuffer` 显式配置 `do-retransmission` / `rtx-*`，探针确认 205/206 出站，读 `rtx-count/rtx-success-count`；
3. T8：音频 jb 在 `rtpbin` 双流闭环下复测 A/V；
4. 产出 L0 v3，冻结本地媒体层。

### Step 1：笔记本接收端准备

1. 确认笔记本以太网 `192.168.240.2`，无默认路由（管理/媒体分开）；
2. Windows 防火墙放行 UDP 5004/5006（或 Linux VM 桥接，避免 Windows 防火墙）；
3. 安装/验证 GStreamer：
   ```text
   gst-launch-1.0 --version
   gst-inspect-1.0 rtpbin
   gst-inspect-1.0 rtpjitterbuffer
   gst-inspect-1.0 rtph264depay
   gst-inspect-1.0 rtpopusdepay
   ```
4. 先用本地 UDP 回环在笔记本上验证接收管线，再接 Pi。

### Step 2：L1 真实无线 UDP baseline

前置：

```text
# Pi 上重新应用策略路由（重启后会丢）
sudo bash /home/bai/rtc_test/setup_media_route.sh
ip route get 192.168.240.2 from 192.168.240.126
# 必须显示 dev wlan1
```

发送：

```text
Pi wlan1 .126 → AP .1 → 笔记本 .2:5004
```

先做 **10 Mbps 视频-only**：

- AP `phy0.1-ap0` 抓到 RTP；
- Pi `wlan1` TX 增量 ≈ 码率 × 时长；
- 笔记本接收并解码，源帧数 = 解码帧数；
- 记录帧完整率、解码率、时延/抖动、CPU、AP station rx/airtime/retries。

然后 M2：

- Opus + RTCP SR；
- 锚点素材测 A/V skew；
- SRTP；
- 丢包/NACK/PLI/RTX（T7 闭环后）。

### Step 3：冻结 UDP baseline

只有以下都过，才允许冻结：

```text
L0 T3/T4 302/302
L0 T7 反馈闭环
L0 T8 音频 jb/rtpbin 闭环
L1 真实无线 clean baseline + 指标
```

### Step 4：L2 替换

- 在 Pi 写 `l2sink`，在笔记本写 `l2src`；
- 同一套 RTP/RTCP/SRTP；
- 目的 MAC = 笔记本以太网 MAC；
- AP 只 bridge；
- 与 UDP baseline 同素材/同编码/同接收端/顺序跑；
- 对比帧完整率、解码率、抖动、A/V skew、时延、画质；
- 未受影响功能回归；受影响功能补丁。

---

## 6. 当前必须先解决的两个事实

1. **Pi 的策略路由当前在位，但重启后会丢失**：当前 `ip rule` 有 `from .126 lookup 100`，`table 100` 指向 `wlan1`；每次发送前仍要用 `ip route get <接收端IP> from 192.168.240.126` 复核出口，重启后执行 `setup_media_route.sh`。
2. **笔记本接收栈尚未建立**：Windows 无 GStreamer；WSL2 不适合 L2；需要拍板 Windows 原生 + 小应用，还是 Linux VM 桥接。

---

## 7. 建议的决策

- **基线阶段**：如果能在笔记本上跑 Linux VM，优先 Linux VM（桥接以太网），一次性解决 GStreamer/SRTP/l2src；
- 如果暂时没有 VM：先用 Windows 原生 GStreamer 做 **UDP 视频-only baseline**，SRTP/L2 接收端后置，不要把两者混在一个未验证的 Windows 栈里；
- **AP 不再装 GStreamer/Pion**；之前 AP 接收端的调试工作从关键路径移除。

---

## 8. 一句话

新场景把接收端从 AP 移到笔记本，**AP 只做 bridge**；这简化了 AP，但把工程难点转移到 Windows 接收栈、SRTP 密钥回调和 L2 收包。  
下一步仍然是：**L0 收口 → 笔记本接收端 → L1 真实无线 UDP baseline → 冻结 → L2 对比 → 补丁**。
