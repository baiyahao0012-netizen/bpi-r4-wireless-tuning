# per-STA VIP 方案 A/B 对比测试（2026-10-22）

## 方案 A：mac80211 txq 层 `airtime_weight`

mt76 的 TX 调度实际调用 mac80211 的 `ieee80211_next_txq()`；mac80211 已实现 per-STA airtime DRR，权重通过 `sta->airtime_weight` 配置：

```sh
iw dev phy0.1-ap0 station set <MAC> airtime_weight <weight>
```

测试条件：两个 5G STA 同时 TCP 下行 5 s，权重 1024（VIP）vs 64（普通），并用 debugfs `stations/<MAC>/airtime` 读取 TX airtime 增量。

### 测试 1：VIP 放在较慢的 Realtek 8812BU（40:a5:ef:26:e3:47）

| STA | 权重 | 吞吐 | TX airtime 增量 |
|---|---|---|---|
| WLAN5 Realtek（VIP） | 1024 | 140 Mbit/s | 2.46 s |
| WLAN3 MediaTek（普通） | 64 | 183 Mbit/s | 1.24 s |

结果：VIP 吞吐反而低 23%。原因是 Realtek 链路速率低（VHT 585 Mbps），即使拿到更多 airtime，吞吐也上不去。

### 测试 2：VIP 放在较快的 MediaTek USB（90:de:80:1c:6a:7a）

| STA | 权重 | 吞吐 | TX airtime 增量 |
|---|---|---|---|
| WLAN3 MediaTek（VIP） | 1024 | 174 Mbit/s | 1.18 s |
| WLAN5 Realtek（普通） | 64 | 152 Mbit/s | 2.57 s |

结果：VIP 吞吐高约 14.5%，但没有达到 16:1 的权重比例。

### 方案 A 结论

- `airtime_weight` 确实被驱动/固件消费（station dump 可读、airtime 计数有变化），但它是**airtime 公平**，不是**吞吐公平**；
- 权重 16:1 只换来约 +14.5% 的吞吐（VIP 在快 STA 上），VIP 放在慢 STA 上甚至更差；
- 对“VIP 通道走更多量”的目标，方案 A 只能算**弱 VIP**，不能做到 2x/4x。

## 方案 B：mt7996 驱动/WCID 层加权

代码路径：`mt76_txq_schedule_list()` 调用 `ieee80211_next_txq()`，也就是说 mt76 自己并不维护 per-STA 队列轮转，而是把调度交给 mac80211。

要做方案 B，需要：

1. 在 `mt76_txq_schedule_list()` 里绕过/替换 `ieee80211_next_txq()`，自己按 WCID 权重选 txq；
2. 或者让 mt7996 固件提供 per-WCID 队列权重/airtime 配置命令；
3. 还要避免与 mac80211 的 fq/ATF 重复调度。

现状：**方案 B 未实现，无法给出实测数据**；从代码路径看，它比 A 更重、更容易和固件调度冲突。

## 结论：哪个更好

| 维度 | 方案 A（mac80211 airtime_weight） | 方案 B（mt7996 WCID/固件） |
|---|---|---|
| 是否已有实现 | 有，标准 nl80211/iw | 无，需要新驱动/固件接口 |
| 实测 VIP 效果 | +14.5%（VIP 在快 STA）；VIP 在慢 STA 为负 | 未实现，无数据 |
| 代码侵入性 | 低，无需改内核 | 高，需绕过 mac80211 txq 调度 |
| 风险 | 低，但效果弱 | 高，可能被固件覆盖 |

**推荐：先走方案 A**，但要把“VIP=更多吞吐”定义清楚：

- 如果 VIP 只要求“更多 airtime/更低时延”，A 够用；
- 如果 VIP 要求“吞吐 2x/4x”，A 不够，需要 **weight × rate** 的联合调度，或方案 B 的固件 per-WCID 权重；
- 在 A 上继续调试的成本远低于 B；只有确认 A 在固件层完全无效时，才值得做 B。
