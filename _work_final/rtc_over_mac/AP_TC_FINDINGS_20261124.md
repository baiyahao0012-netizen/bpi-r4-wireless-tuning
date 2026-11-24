# AP 侧 TC 调度实验（2026-11-24）

## 目的

按仿真结构把调度器放到 **AP 的出口队列**（仿真里 `QuotaWifiQueueScheduler` / `AiFirstWifiQueueScheduler` 所在的 AC_BE 队列位置），验证"AI 优先"在真实 MAC 侧是否成立。

## 方法

- **AP 侧源发流量**：静态编译的 `l2_ai_ap_tx`（aarch64 静态 ELF，Pi 上交叉编译）直接在 AP 运行：
  - 收 Pi 的 `0x88B6` 请求 → 回 `0x88B6` 响应（1200 B）；
  - 同时按目标速率发 `0x88B7` bulk（1400 B）。
  - 两个 socket 分别设 `SO_PRIORITY 0`（AI）/ `SO_PRIORITY 1`（bulk）。
- **分类**：AP 上 `u32 match u16 0x88b6 at 12` **不命中**（桥接帧与 AP 源发帧均如此）；改用
  `tc filter ... basic match "meta(priority eq 0)" flowid 1:10`，稳定命中。
- **队列**：`htb` 根 qdisc，1:10 = AI，1:20 = bulk。
- **测量**：Pi 跑 `l2_ai_client.py`，TTFT = t3−t0；bulk 实际吞吐由 AP 侧发送计数换算，并在 Pi 端核对 `bulk_rx`。

## 结果（bulk 目标 40 Mbps，AI 8 次/秒，8 秒）

| 臂 | TTFT p50 | TTFT p95 | bulk 实际 | AP 类统计 |
|---|---:|---:|---:|---|
| 无 TC | **6.7 ms** | 20.3 ms | 39.6 Mbps | — |
| HTB，两类同 20 Mbit，AI prio 0 | 11.1 ms | 31.9 ms | 20.0 Mbps | 1:20 overlimits 25,014 |
| HTB，AI 200 Mbit prio 0，bulk 20 Mbit | 13.0 ms | 67.1 ms | 19.9 Mbps | 1:20 overlimits 24,838 |
| HTB，AI 200 Mbit prio 0，bulk 10 Mbit | 23.9 ms | 58.9 ms | 10.1 Mbps | 1:20 overlimits 12,574 |

AI 帧确实进入 1:10（707 包 / 875 KB），分类成立；bulk 确实被限速（overlimits 与吞吐对应）。

## 结论

1. **TC 优先级/限速没有改善 AI 时延，反而变差**（6.7 → 11–24 ms）。
2. 原因：HTB 是**排队式**限速。bulk 在 TC 层积压后，AI 包被放行时仍要排在 **mt76 驱动的 AC_BE FIFO** 之后；TC 位于驱动队列之前，无法改变驱动队列内部的顺序。
3. 因此 **用户态/TC 层测到的 8× 是"队列位置"造成的**，在真实 MAC 队列上不复现——与此前批评一致。
4. 丢弃式限速（等价于仿真 quota 的"丢弃而非排队"）在本 AP 上不可用：`act_police` 模块不存在（`Failed to load TC action module`）。

## 对方案的含义

- 要在 MAC 层真正做"AI 优先"，AP 侧可用的旋钮只剩 **per-STA** 的 `airtime weight` 与 per-STA AQL（需要 AI 与 bulk 分属不同 STA）；
- 同 STA 内按流优先，在 mt76 上**没有可控入口**（驱动队列不可编程）；
- 应用层实现（A 档）仍然是唯一能完整演示"反馈 + 两个调度器"的地方，但结论必须标注"应用层等价实现"，不能外推为 MAC 行为。

## 复现脚本

- `tools/l2_ai_ap_tx.c`（AP 侧发送器，静态编译）
- `tools/run_ap_tc_matrix.sh`（四臂矩阵）
- `tools/test_ap_htb_throttle.sh`（HTB 限速验证）
- `tools/setup_ap_basic_filter.sh` / `check_ap_classes.sh`（分类与计数）
