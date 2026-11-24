# AP 侧调度实验（2026-11-24，v2：容量与拥塞修正）

## 1. 先修正上一版的三个前提错误

| 上一版说法 | 实测修正 |
|---|---|
| "40 Mbps 就该有拥塞" | **错**。链路真实容量 **215 Mbps**（iperf3 UDP 400M offered → 215 Mbps 达成）；40 Mbps 只是 19% 负载 |
| "66 Mbps 是链路容量" | **错**。66 Mbps 是 C 发送器（单线程 sendto）的上限，不是链路 |
| "TC 无效" | **不准确**。TC 分类与限速都成立（1:10 = 702 包 / 874,692 B = 1246 B/包，与 AI 帧长一致）；但 TC 是排队式整形，**它自己引入的排队延迟**大于它能省下的时间 |

## 2. 真拥塞下的数据（iperf3 bulk 300M offered → 207 Mbps 达成，无 TC）

| 臂 | TTFT p50 | TTFT p95 | bulk 达成 | aql_pending (BE) |
|---|---:|---:|---:|---:|
| AI prio 0（同 TID） | **7.24 ms** | 14.3 ms | 207 Mbps | **2228 µs** |
| AI prio 3（TID 3） | 7.85 ms | 26.1 ms | 213 Mbps | 2252 µs |
| AI prio 0，bulk 150M | 3.87 ms | 12.0 ms | 145 Mbps | 0 |

- 拥塞把 AI 时延从 ~2.3 ms（无拥塞）抬到 7.2 ms；
- `aql_pending` 约 2.2 ms，与增量同量级 → **延迟主要落在驱动/空口的在途排队**；
- **TID 隔离没有效果**：prio 3 与 prio 0 相同（甚至 p95 更差）。

## 3. TC 层实验（饱和前的四臂，作对照）

| 臂 | TTFT p50 | bulk 实际 | 1:10 backlog | 说明 |
|---|---:|---:|---:|---|
| 无 TC（40M offered） | 6.7 ms | 39.6 Mbps | — | 轻载 |
| HTB 两类同 20M，AI prio 0 | 11.1 ms | 20.0 Mbps | 0 | 变差 |
| HTB AI 200M，bulk 20M | 13.0 ms | 19.9 Mbps | 0 | 变差 |
| HTB AI 200M，bulk 10M | 23.9 ms | 10.1 Mbps | 0 | 更差 |

- `1:10 backlog = 0`、`aql_pending` 仅 12–48 µs → **TC 不是瓶颈，也不是延迟来源**；延迟来自 HTB 自身的排队（bulk 积压在 TC 层，AI 放行后被驱动队列的既有 bulk 帧挡住）；
- 且 bulk 限得越低，AI 越差（10M > 20M），说明是"TC 排队深度"主导。

## 4. 结论（可写进报告的证据链）

1. 链路容量 ~215 Mbps；要制造拥塞，offered 必须 ≥ 300 Mbps。
2. 真拥塞下，单 STA 内 AI 的额外延迟 ≈ 2–5 ms，来源是 **mac80211/mt76 的 AC_BE 在途队列**（`aql_pending` 可证），而非 TC。
3. **TC 不能降低这段延迟**：它位于驱动队列之前，只能排队/整形，自己还会增加延迟。
4. **TID 隔离（prio 3/5）也不能**：同一 AC 内不同 TID 共享 AQL 预算与聚合机会，实测无差别。
5. 因此，**同 STA 内按流优先在这套硬件上没有可控入口**；剩余的 MAC 层手段只有 **per-STA** 的 `airtime weight` 与 per-STA AQL（要求 AI 与 bulk 分属两个 STA）。

## 5. 复现

- `tools/l2_ai_ap_tx.c`：AP 侧 AI 响应器（静态编译），`argv[6]` = AI 的 SO_PRIORITY
- `tools/test_capacity_iperf.sh`：链路容量
- `tools/test_congestion_real.sh`：真拥塞 + TID 对照
- `tools/test_tc_saturated.sh`：TC 四臂 + AQL 采样
- 分类：`basic match "meta(priority eq 3)"` + `SO_PRIORITY`（`u32` 的 EtherType 匹配在本 AP 上不命中）

## 6. 两 STA 实验（per-STA AQL / airtime weight）

拓扑：wlan0（板载 brcmfmac，192.168.240.150）作 bulk STA，wlan1（mt7921u，.126）作 AI STA；bulk 为 AP→wlan0 下行（iperf3 UDP 300M offered），AI 为 AP→wlan1。

| 臂 | TTFT p50 | TTFT p95 | bulk 达成 | aql_pending | bulk STA 的 AQL |
|---|---:|---:|---:|---:|---|
| 默认（5000/12000） | 6.25 ms | 11.9 ms | 155 Mbps | 1804 µs | 5000/12000 |
| bulk AQL 压到 2000/6000 | **5.78 ms** | 14.7 ms | 161 Mbps | 1712 µs | 2000/6000 |
| airtime weight 128 | 6.29 ms | 19.5 ms | 148 Mbps | 2608 µs | 5000/12000 |

- 压低 bulk STA 的 AQL 只带来 **~8% 的 p50 改善**，p95 反而变差；
- airtime weight 调低 **没有效果**；
- bulk STA 的 `Q depth` 读数为 **0 µs**（即使 155 Mbps 下行），说明 AQL 的 pending 记账没有反映该 STA 的实际积压——这解释了为什么 AQL 限额几乎不起作用；
- bulk 吞吐被第二射频（brcmfmac，~155 Mbps）限制，不是 AP。

## 7. 总证据链

| # | 结论 | 证据 |
|---|---|---|
| 1 | 链路容量 ~215 Mbps | iperf3 UDP 400M offered → 215 Mbps |
| 2 | 真拥塞下 AI 额外延迟 ~2–5 ms | TTFT 2.3 ms（无拥塞）→ 7.2 ms（207 Mbps bulk），aql_pending 2228 µs |
| 3 | TC 不能降低该延迟 | 四臂：加 TC 后 11–24 ms，1:10 backlog=0，延迟来自 HTB 自身排队 |
| 4 | TID 隔离无效果 | prio 0 vs 3：7.24 vs 7.85 ms |
| 5 | per-STA AQL 只有边际效果 | 6.25 → 5.78 ms（~8%），p95 变差；Q depth=0 |
| 6 | airtime weight 无效果 | 128 vs 256：6.29 vs 6.25 ms |

**结论**：在这套硬件（mt76 AP + mt7921u/brcmfmac STA）上，**同 STA 内按流优先没有可控入口**；跨 STA 的 per-STA 旋钮也只有边际效果，且 AQL 记账在该路径上不可靠。应用层实现是唯一能完整、稳定演示"反馈 + 两个调度器"的地方，但必须标注为"应用层等价实现"。
