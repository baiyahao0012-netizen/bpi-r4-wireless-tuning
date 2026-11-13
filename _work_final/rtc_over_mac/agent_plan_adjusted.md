确认，按你这两条调整后，方案是自洽的：

- **不派生 10/15/20 Mbps，直接用你给的六条 1080p 视频跑完整时长；**
- **本轮只做 B：RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC，去掉 UDP/IP，但 RTC 层保留。**

我已把这版写入 [REVISED_PLAN_20261112.md](_work_final/rtc_over_mac/REVISED_PLAN_20261112.md)。

---

## 一、准备工作已完成

六条视频已复制到 Pi：

```text
/home/bai/rtc_test/testset_1080p/
```

并已用 ffprobe 核对：

| 文件 | fps | 时长 | 视频码率 | 帧数 |
|---|---:|---:|---:|---:|
| `1080p24_1_sintel_trailer_52s.mp4` | 24 | 52.21 s | 2.11 Mbps | 1253 |
| `1080p24_2_caminandes_90s.mp4` | 24 | 90.04 s | 7.00 Mbps | 2161 |
| `1080p25_3_bbb_trailer_33s.mp4` | 25 | 32.48 s | 7.16 Mbps | 812 |
| `1080p30_1_artemis_origins_85s.mp4` | 30 | 85.33 s | 5.00 Mbps | 2560 |
| `1080p30_2_artemis_avatar_76s.mp4` | 30 | 75.77 s | 5.00 Mbps | 2273 |
| `1080p30_3_artemis_recap_90s.mp4` | 30 | 90.07 s | 5.02 Mbps | 2702 |

Pi 的策略路由已恢复：

```text
ip rule: from 192.168.240.126 lookup 100
table 100: 192.168.240.0/24 dev wlan1
发送守卫：dev wlan1 table 100
```

但 **策略路由重启后会丢**，每次测试前仍要复核。

---

## 二、当前真正的阻塞点

网络平台已通，但笔记本接收栈还没完成：

- 没有 GStreamer；
- 只有 Python/PyAV 探针；
- 探针只能做 clean-path 冒烟，不能做完整媒体层测试。

所以现在的状态是：

```text
网络路径：已验证
六条素材：已就位
正式 UDP baseline：还不能开跑
```

---

## 三、修订后的完整测试流程

### P0：L0 媒体层收口

- T3/T4 显式 EOS → 源帧数 = 解码帧数；
- T7 NACK/PLI/RTX 闭环；
- T8 音频 jb/rtpbin 双流；
- 产出 L0 v3。

### P1：笔记本正式接收端

优先：

```text
Linux VM 桥接以太网 + GStreamer
```

或先：

```text
Windows 原生 GStreamer runtime（clean UDP）
```

要求：

- 绑定 `192.168.240.2`；
- 收 5004/5006；
- 防火墙放行；
- 记录 PC/Pi 时钟偏移。

### P2：UDP baseline（A）

用六条原始视频，**逐条跑完整时长**：

1. 先 `1080p30_1` 全片 smoke；
2. 再六条全跑；
3. 先视频-only；
4. 再加音频/A-V sync。

每条记录：

- 源帧数 / 解码帧数；
- RTP 包数、seq gap、SSRC、PT；
- 时延、抖动、帧完整率；
- Pi CPU/温度；
- AP airtime/retries/rx bytes；
- 路由/计数器对账。

### P3：冻结 UDP baseline

只有 P0 + P2 都过，才能冻结。

### P4：L2（B）

```text
RTP/RTCP/SRTP → L2 shim → Wi-Fi MAC
```

- `l2sink` / `l2src`；
- EtherType `0x88B5`；
- 目的 MAC = 笔记本以太网 MAC；
- AP 只 bridge；
- 同一六条视频、同一接收端、同一指标；
- pcap 确认无 IP/UDP 头。

### P5：影响矩阵 + 补丁

- 未受影响：编解码、RTP 载荷、SSRC/PT、A/V PTS、SRTP 算法、应用处理；
- 受影响：UDP/IP、端口、MTU/分片、SRTP 上下文、L2 shim、接收抓包、QoS、jitter/pacing；
- 受影响功能补丁；
- 未受影响功能回归；
- 重跑 L2 全量。

### P6：B 验收

- 六条视频完整时长全部通过；
- 无 IP/UDP 头；
- 帧完整率/解码率/抖动/A-V skew 达标；
- 与冻结的 UDP baseline 对比；
- **本轮只到 B，不做 C（RTC 层消失）。**

---

## 四、两个方法学注意点

### 1. 六条素材码率不同，不能跨片比较“码率影响”

它们覆盖 2.1–7.2 Mbps、24/25/30 fps、不同内容。  
正确比较是：

```text
同一条视频：UDP baseline vs L2
```

不是：

```text
24fps 视频 vs 30fps 视频
```

### 2. 完整时长意味着不能用当前 10 s smoke 脚本

`send_pc.sh` 现在是 10 s 冒烟；正式测试要新增：

```text
send_testset.sh
```

按每条视频的真实时长发送，并让发送端正常 EOS，避免 301/302 的尾部截断。

---

## 五、下一步

1. 笔记本装 GStreamer 或 Linux VM；
2. 修 `w32time`，记录 PC/Pi 时钟偏移；
3. 新增 `send_testset.sh`，支持六条全片；
4. 先用 `1080p30_1` 全片跑 GStreamer UDP 接收，确认源帧数 = 解码帧数；
5. 再跑六条 UDP baseline；
6. 冻结后进入 B（L2）。

**结论：你的两条约束和当前方案一致；现在缺的不是方向，而是笔记本正式接收端和全片测试脚本。**