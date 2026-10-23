# BPI-R4 无线参数实时性与私有调度器实验总结

> 版本：2026-10-23 · 供汇报/二次撰写使用
> 环境：Bananapi BPI-R4 2.5GE PoE，OpenWrt 24.10.0 r28427，内核 6.6.73，MT7996（BPI-R4-NIC-BE14）

## 0. 环境、拓扑与前提

### 0.1 硬件与系统

| 项目 | 配置 |
|---|---|
| 开发板 | BPI-R4 2.5GE PoE，MT7988A |
| 系统 | OpenWrt 24.10.0 r28427-6df0e3d02a |
| 内核 | 6.6.73 |
| WiFi | MT7996，2.4G + 5G AP（6G 未启用） |
| 5G AP | phy0.1-ap0，SSID BPI-R4-5G，ch149，HE80，Tx 26 dBm |
| 2.4G AP | phy0.0-ap0，SSID BPI-R4，ch6，HE20 |
| 板端上行 | phy0.0-sta0 连手机热点 Bai（2.4G），为板端/PC 提供外网 |

### 0.2 PC 侧网卡

| 接口 | 型号 | 能力 | 实测/用途 |
|---|---|---|---|
| WLAN | Realtek 8852CE（PCIe） | 2.4/5/6G，ax，5G 1201 | 单流仅 29 Mbit/s，异常，未用于正式对比；用于 CUG 上网 |
| WLAN 3 | MediaTek MT7921AU（USB） | 2.4/5/6G，ax，5G 1201 | 单流 369–422；最佳 5G STA |
| WLAN 5 | Realtek 8812BU（USB） | 2.4/5G，ac，5G 866 | 单流 211–232；5G 普通 STA |
| WLAN 6 | Ugreen USB WiFi（A69C:88DE） | 标称 3 频，实际 2.4G 可用 | 2.4G 同型号对 |
| WLAN 7 | Ugreen USB WiFi #2（同型号） | 同上 | 2.4G 同型号对 |

### 0.3 重要前提

- 板端 MT7996 卡内 EEPROM 读取异常，当前 mt7996e 使用“强制默认 EEPROM”诊断构建；绝对吞吐与完全原厂校准状态会有差异，所有对比均为同构建/同链路条件下的相对测量。
- 测试期间 6G 未启用；2.4G 与板端 STA 到 Bai 共用射频，部分 2.4G 测试通过临时禁用 sta0 获得干净 AP。
- 两个 USB WiFi 网卡同时高负载会互相影响（5G USB 可能掉线），跨频测试采用 5G 先启动、2.4G 限速 5 Mbit/s 的方式规避。

## 1. 任务一：EDCA / A-MPDU / MCS 实时性系统实测

### 1.1 目的

1. 验证 EDCA（AIFS/CWmin/CWmax/TXOP）、A-MPDU 聚合窗口、MCS 速率三类参数在 AP 运行中调整是否即时生效；
2. 明确是否需要重载 WiFi；
3. 定量给出从用户态命令到固件/空口/业务可见的时延量级；
4. 明确 OpenWrt 软件队列、固件、硬件三层的最小调度粒度。

### 1.2 方法

#### EDCA

- 路径：nl80211 `SET_WIPHY + WIPHY_TXQ_PARAMS` → `ieee80211_set_txq_params()` → `link->tx_conf[ac]` → `drv_conf_tx()` → `BSS_CHANGED_QOS` → `mt7996_link_info_changed()` → `mt7996_mcu_set_tx()` → 固件 `EDCA_UPDATE`。
- 工具：自写 aarch64 静态 C 工具 `edca_set`，直接发 nl80211 报文，绕过 hostapd；进程内 `CLOCK_MONOTONIC` 测 sendto→内核 ACK（ACK 在固件 EDCA_UPDATE 响应之后返回）。
- 回读：驱动 `mt7996_mcu_set_tx()` 内增加 `last_edca[]` 快照，debugfs `edca` 按固件 ACI 顺序打印 4 个 AC 的 raw 值与 fls 值。
- 免重载验证：切换期间记录 hostapd PID、STA connected time、iperf3 吞吐/重传。
- 混合 AC：用 AF_PACKET 直接注入以太网帧，`SO_PRIORITY=262`（VO）、`257`（BK）或 `256`（BE），因为 mac80211 的 `cfg80211_classify8021d()` 会覆盖普通 SO_PRIORITY，256–263 才会直接映射 802.1d 优先级。

#### A-MPDU

- 驱动增加 `agg_win_cap` debugfs；写入时对所有已关联 STA 重放 TX BA TLV（先删后加），把 `buf_size` 截断到 cap；0 表示恢复默认窗口。
- 用 iperf3 反向（板端 server，PC 下行）测吞吐；写 cap 前后对比。

#### MCS

- 路径 1：`iw dev phy0.1-ap0 set bitrates ...`，走 cfg80211/driver rate mask；
- 路径 2：驱动 `force_mcs` debugfs（0–7 强制 MCS，255 自动），在 `sta_rec_ra_info` 组包时覆盖 `rx_mcs_bitmask`；
- 记录 station tx bitrate、吞吐、dmesg。

### 1.3 实验结果

#### 1.3.1 EDCA 回读

hostapd 启动后的初始值（固件 ACI：0=BE 1=BK 2=VI 3=VO）：

| ACI | aifs | cwmin | cwmax | txop | fls(cwmin/cwmax) |
|---|---|---|---|---|---|
| 0 BE | 3 | 15 | 63 | 0 | 4 / 6 |
| 1 BK | 7 | 15 | 1023 | 0 | 4 / 10 |
| 2 VI | 1 | 7 | 15 | 94 | 3 / 4 |
| 3 VO | 1 | 3 | 7 | 47 | 2 / 3 |

把 BE 改为 aifs=3 / cwmin=7 / cwmax=15 / txop=0 后，同一节点立即回读为 3/7/15/0，fls 变为 3/4；全程没有重启 hostapd、没有 down/up 接口。

#### 1.3.2 EDCA 下发时延

| 场景 | 样本 | min | p50 | p95 | max |
|---|---|---|---|---|---|
| 连续切换（空载） | 50 | 147.2 μs | **220.3 μs** | 381.5 μs | 884.6 μs |
| 20 s 打流中切换 | 15 | 235.8 μs | **300.7 μs** | 550.5 μs | 689.0 μs |
| 三流并发打流中切换 | 30 | 170.7 μs | **341.8 μs** | 562.4 μs | 1064.9 μs |

说明：时延口径为 sendto(nl80211)→内核 ACK，包含 host→mac80211→驱动→固件→ACK 的完整往返；不是单纯用户态系统调用耗时。

#### 1.3.3 EDCA 免重载与业务连续性

- hostapd 进程 PID 全程不变（1919/1867 → 1919/1867）；
- STA connected time 从 61 s 连续增长到 76 s，无 deauth/assoc；
- 20 s 下行 iperf3：平均 371 Mbit/s，逐秒 343–397 Mbit/s，全程无 0 吞吐空档，Retr=0；
- 切换 15 次期间无 hostapd “Could not set interface … UP”、无 MCU timeout。

#### 1.3.4 混合 AC 竞争（VO vs BK）

条件：板端 5G AP，单个 PC STA，AF_PACKET 注入两路 UDP，100 ms 分桶。

| 阶段 | VO 平均 | BK 平均 | VO:BK |
|---|---|---|---|
| 0–6 s 默认 EDCA | 88.3 Mbit/s | 2.4 Mbit/s | **36.2:1** |
| 6–12 s VO 激进（1/1/3/94） | 96.9 Mbit/s | 2.4 Mbit/s | 40.8:1 |
| 12–20 s BK 激进（1/1/3/94） | 2.0 Mbit/s | 218.2 Mbit/s | **1:109** |

12 s 切换的 100 ms 分桶：12.0–12.1 s 仍 VO 113.4/BK 0.2；12.1–12.2 s 变 46.7/94.6；12.2–12.3 s 变 0/175.8；12.3–12.4 s 进入新稳态 0/244.3。

结论：只有 EDCA 参数改变、两条流发送逻辑相同，VO:BK 从 36:1 翻转到 1:109；业务可见变化 0.1–0.2 s 内出现，0.2–0.3 s 进入稳态。

补充：VO vs BE（同一注入方式）为 99.7 vs 36.3 Mbit/s，约 **2.75:1**。

#### 1.3.5 A-MPDU 聚合窗口

| 配置 | 平均吞吐 | 逐秒范围 | Retr |
|---|---|---|---|
| cap=0（默认） | 381 Mbit/s | 363–394 | 2 |
| cap=2（≤2 MPDU/A-MPDU） | **74.3 Mbit/s** | 63–78 | 0 |
| cap=0（恢复） | **402 Mbit/s** | 387–419 | 0 |

- 写入 `agg_win_cap=2` 的 write() 时延：**11.5 ms**（3 个 STA 的 BA 重放）；写回 0：**10.5 ms**；
- 首个 STA 的吞吐在 0–0.5 s 内开始下降，第二个 STA 约 2.5 s，完全进入新稳态约 3 s，恢复约 3.5 s；
- dmesg：`agg_win_cap: cap=2 applied to 3 station(s)` / `cap=0 applied to 3 station(s)`；
- 历史对照数据：185→92 Mbit/s（−50.3%），趋势一致，绝对基线取决于链路/终端。

#### 1.3.6 MCS 锁定

| force_mcs | station tx bitrate | 下行吞吐 | 结果 |
|---|---|---|---|
| 0 | 864.8 Mbit/s HE-MCS8 | 348 Mbit/s（8 s） | 未锁到 MCS0 |
| 1 | 960.7 Mbit/s HE-MCS9 | 342 Mbit/s（6 s） | 未锁到 MCS1 |
| 255（自动） | 960–1080 Mbit/s | 371–402 Mbit/s | 正常 |

- `force_mcs` 节点可读可写（0/1/255 回读正确），写入时延 6.2–6.8 μs（仅内存变量，无 MCU 命令）；
- station tx bitrate 与吞吐不随锁定值变化，dmesg 也没有 `mt76: FORCE MCSx`；
- 根因：mt7996 设置 `ieee80211_hw_set(hw, HAS_RATE_CONTROL)`，使用**固件 RC**，不是 minstrel_ht；`iw set bitrates` 在 cfg80211/driver 层被接受并下发，但固件 RC 的 AP 下行速率表不按该 mask 执行；仅覆盖 `rx_mcs_bitmask` 也不足以锁速。
- 结论：MCS “命令可下发”成立，“AP 下行实时生效”不成立；真正锁速需改固件 rate table 或走 STA 模式。

### 1.4 最小调度粒度

| 层 | 最小可控单位 | 依据 |
|---|---|---|
| OpenWrt 软件队列 | **skb / flow** | mac80211 fq/txq 以 skb 入队；DRR 以 flow 轮转；`quantum` 可按 flow 设置 |
| 固件 | **一次 MCU 命令 / 一个 BA TLV（per TID）** | EDCA_UPDATE 一次下发 4 个 AC；命令往返 147–885 μs |
| 硬件 | **一个 PPDU / 一个 A-MPDU** | PPDU 是最小发送单位；A-MPDU 可含多个 MPDU；cap=2 使吞吐 402→74.3 |

说明：TXOP 的 32 μs 单位、slot 的 9 μs 是 **EDCA 参数单位/竞争单位**，不是“调度粒度”；463.5 μs 是历史下发时延，也不是粒度。

### 1.5 任务一结论

1. **EDCA**：运行中走 nl80211 下发，**微秒–亚毫秒级**生效（p50 220–342 μs），**不需要重载 WiFi**；混合 AC 下 VO/BK 比例可在 0.1–0.3 s 内翻转。
2. **A-MPDU**：debugfs 写 BA 窗口 **10.5–11.5 ms**（3 STA），业务吞吐在 **0.5–3 s** 内进入新稳态，**不需要重载**。
3. **MCS**：命令可下发、节点可写，但 AP 下行 **不生效**（固件 RC，不是 minstrel_ht）；这是负结果，不是“没做完”。
4. **最小粒度**：软件 skb/flow，固件 MCU 命令/BA TLV，硬件 PPDU/A-MPDU；不存在比 PPDU 更细的硬件调度单位。

## 2. 任务二：私有 WDRR 调度器 coding / 编译 / 部署 / 运行验证

### 2.1 目的

基于现有 mac80211 fq（DRR）代码完成一次私有调度器修改，跑通“修改→编译→烧录→加载→运行验证”链路；并验证 per-AC 加权能否改变 AC 级调度结果。

### 2.2 实现

共 5 处修改：

1. `include/net/fq.h`：`struct fq_flow` 增加 `int quantum;`；
2. `include/net/fq_impl.h`：`fq_tin_dequeue` 出队轮转改为 `flow->deficit += flow->quantum ? flow->quantum : fq->quantum;`；
3. `fq_flow_init`：`flow->quantum = 0`；
4. `net/mac80211/tx.c`：增加 `fq_weight[IEEE80211_NUM_ACS]` 模块参数（默认 1,1,1,1）；
5. 首次 dequeue 时按 `txqi->txq.ac` 赋 `flow->quantum = fq->quantum * fq_weight[ac]`，并 `printk_once` 标记。

### 2.3 编译与部署

| 项目 | 结果 |
|---|---|
| 产物 | mac80211.ko，6,603,848 B |
| md5 | `49f2aca91f3228adcd83b205f5338d61` |
| 符号/字符串 | `fq_weight`、`__param_fq_weight`、`private WDRR scheduler active` 均在产物中 |
| 烧录 | 覆盖 `/lib/modules/6.6.73/mac80211.ko`；原厂备份 `mac80211.ko.stock`（`d562…`） |
| 加载 | `lsmod` 正常；`/sys/module/mac80211/parameters/fq_weight` 存在 |
| 参数读写 | 默认 1,1,1,1；写 4,1,1,1 后回读 4,1,1,1 |
| 运行标记 | dmesg：`mac80211: private WDRR scheduler active (fq_weight=1,1,1,1)` |

### 2.4 调度效果验证

- **per-AC 加权**：历史双 AC（BE/VO）4:1 权重下，吞吐比仍约 1:1；
- 原因：fq 是 **per-flow** 粒度，AC 级调度发生在 **txq 层**；同一 txq 内所有 flow 同 AC，per-AC 权重互相抵消；
- **per-STA VIP 未实现**：`flow->quantum` 只按 `txq.ac` 赋值，没有 STA 维度；不同 STA 同 AC 得到相同权重；
- **现有实现限制**：`flow->quantum` 只在 flow 首次 dequeue 时赋值，已存在的 flow 不受后续 sysfs 修改影响。

### 2.5 VIP 方案探索（补充实验）

#### A. mac80211 `airtime_weight`

| 场景 | VIP 吞吐 | 普通吞吐 | 说明 |
|---|---|---|---|
| VIP 在慢 STA（Realtek 8812BU，1024 vs 64） | 140 Mbit/s | 183 Mbit/s | VIP 反而更慢 |
| VIP 在快 STA（MediaTek，1024 vs 64） | 174 Mbit/s | 152 Mbit/s | 仅 +14.5% |

结论：ATF 是 airtime 公平，不是吞吐公平；权重 16:1 只换来约 +14.5%，且 airtime 计数受队列/速率干扰，不能判定为稳定可用的 VIP。

#### B. AC 策略 VIP（nft DSCP → VO/VI）

实现：`/root/vip_set.sh <VIP_IP>` 在 nft `output` 链给 VIP 目的 IP 打 DSCP EF（VO）；普通 BE。

| 组 | 场景 | 结果 |
|---|---|---|
| 5G 同频（VIP=WLAN3 快 STA） | 基线 161.3/133.3；VIP 147.0/70.9 | 相对 **2.07:1**，VIP 绝对值不高于基线 |
| 5G 同频（VIP=WLAN5 慢 STA） | VIP 80.2 / 普通 112.2 | VIP/普通 **0.71**，慢 VIP 无效 |
| 2.4G 同型号（VIP=WLAN6/7） | 基线 11.4/9.3；VIP 41.0/0.8 或 0.0/36.6 | 强优先，但普通几乎饿死 |
| 跨频隔离（VIP 5G / 普通 2.4G） | 基线 403.3/5.00；VIP EF 210.0/5.00 | 隔离 **80.7:1 → 42.0:1** |

补充：

- 2.4G 跨频测试中 2.4G 限速 5 Mbit/s UDP，是为规避两个 USB 网卡同时高负载导致 5G 掉线；80:1 是下限估计；
- 给 5G 打 EF 后，5G 自身从 403 降到 210（VO 队列 TXOP/聚合效率下降），把 VO TXOP 调到 127 后约 231，仍未恢复；
- VI（CS3）测试因 WLAN3 USB 掉线未完成；
- 慢 STA VIP 负对照：WLAN5 76–80 vs WLAN3 112–127，AC 优先级不能弥补 PHY 速率差距。

### 2.6 任务二结论

1. **“修改→编译→烧录→加载→运行标记”链路已完整跑通**；
2. **per-AC 加权在 fq 层架构性无效**，BE:VO=4:1 时吞吐仍约 1:1；
3. **per-STA VIP 没有实现**，当前补丁没有 STA 维度；
4. AC 策略/频段隔离可作为演示方案，但 AC 策略是“相对优先”，慢 STA 无效；精确 2:1/4:1 需要 **A+：mac80211 txq 层 per-STA 权重/预算**；
5. B（mt7996 固件/WCID）未实现，也没有证据证明一定更好；只有 A+ 被固件限制且 MTK 有 per-WCID 接口时才值得做。

## 3. 原始数据与文件位置

| 文件 | 内容 |
|---|---|
| `_work_final/BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx` | 完整实验报告（环境/方法/数据/结论/复现） |
| `_work_final/quantitative_timing.md` | EDCA/A-MPDU/MCS 时延定量汇总 |
| `_work_final/ac_mix_final.csv` | VO/BK 混合 AC 100 ms 分桶原始数据 |
| `_work_final/ac_mix_timeline.png` | VO/BK 时序图 |
| `_work_final/ac_mix_result.md` | 混合 AC 实验说明 |
| `_work_final/vip_5g_results.csv` | 5G VIP（WLAN3/WLAN5）3 轮原始数据（ATF off） |
| `_work_final/vip_5g_results_atf_on.csv` | 5G VIP（ATF on）原始数据 |
| `_work_final/vip_24g_results.csv` | 2.4G 同型号 3 轮原始数据 |
| `_work_final/vip_cross_results.csv` | 跨频隔离 3+3 轮原始数据 |
| `_work_final/vip_matrix_results.csv` | 全网卡同时插入时的 5 组矩阵（有干扰，作对照） |
| `_work_final/vip_policy_results.md` | AC 策略 VIP 6 轮结果 |
| `_work_final/vip_four_groups_summary.md` | 四组 VIP 结果汇总 |
| `_work_final/nic_selection_analysis.md` | 5 个网卡选型分析 |
| `_work_final/vip_ab_test.md` | 方案 A/B 对比 |
| `_work_final/vip_solution_eval.md` | VIP 方案综合评估 |
| `_work_final/vip_analysis_review.md` | 对 A/B 分析的复核与修正 |
| `_work_final/modules/` | EDCA/A-MPDU/MCS 三套 ko、WDRR mac80211.ko、edca_set 二进制/源码 |
| `_work_final/modules/README.md` | 模块 md5 与切换方法 |

说明：EDCA 50/15 次原始时延逐条记录当时写在板端 `/tmp`，板子重启后丢失；统计值（min/p50/p95/max）保留在报告与上表。A-MPDU/MCS 的逐秒 iperf3 输出部分保留在报告/会话记录中，关键汇总值已写入报告。

## 4. 总体结论（可直接用于汇报）

1. **EDCA**：免重载、即时生效，命令→固件 ACK 为 **0.15–1.06 ms（p50 0.22–0.34 ms）**，空口在下一次 TXOP 内生效；VO/BK 比例可在 0.1–0.3 s 内翻转。
2. **A-MPDU**：免重载，debugfs 写 BA 窗口 **10.5–11.5 ms**，业务吞吐 **0.5–3 s** 进入新稳态；cap=2 使下行 402→74.3 Mbit/s（−81.5%）。
3. **MCS**：命令可下发，但 AP 下行 **不生效**；mt7996 使用固件 RC（`HAS_RATE_CONTROL`），不是 minstrel_ht；需固件 rate table 或 STA 模式。
4. **最小调度粒度**：软件 skb/flow；固件 MCU 命令/BA TLV；硬件 PPDU/A-MPDU；TXOP/slot 是参数单位，不是粒度。
5. **私有 WDRR**：修改→编译→烧录→加载→运行标记全链路已跑通；但 per-AC 加权在 fq 层架构性无效，per-STA VIP 未实现；正确层级是 txq/airtime fairness。
6. **VIP 演示**：同频 AC 策略只在 VIP 为快 STA 时有效（2–3:1），慢 STA 无效；2.4G 同型号组效果最强但普通会饿死；跨频隔离最稳（最高 80:1）。
7. **下一步**：要做 2:1/4:1 可配置 per-STA 比例，应实现 **A+（mac80211 txq per-STA 权重/预算）**；B（固件/WCID）仅在 A+ 被下游限制且 MTK 提供接口时再考虑。

## 5. 汇报时的注意事项

- 不要把“EDCA 命令 ACK 时延”说成“空口生效时延”；两者差一个 TXOP/排队，量级分别是百微秒和亚毫秒。
- 不要把“A-MPDU write 10 ms”说成“业务 10 ms 生效”；业务稳态需要 0.5–3 s。
- 不要把“MCS 不生效”说成“没做”；这是有明确根因的负结果。
- 不要把“AC 策略 VIP”说成“可配置 2:1/4:1”；它只能给固定优先级，精确比例需要 A+。
- 跨频 80:1 中 2.4G 被限速 5 Mbit/s，是测试口径，需注明。
