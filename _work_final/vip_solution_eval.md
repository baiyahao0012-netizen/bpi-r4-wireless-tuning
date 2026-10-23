# per-STA VIP 方案综合评估（2026-10-22）

## 目标

让不同 STA 获得不同吞吐：VIP STA 明显更快，普通 STA 被限制但不至于完全断网；要求可配置、可复现、风险可控。

## 已有实测数据

### 方案 A：mac80211 `airtime_weight`

| 场景 | VIP 吞吐 | 普通吞吐 | 结论 |
|---|---|---|---|
| VIP 在慢 STA（Realtek 8812BU，1024 vs 64） | 140 Mbit/s | 183 Mbit/s | VIP 反而更慢 |
| VIP 在快 STA（MediaTek USB，1024 vs 64） | 174 Mbit/s | 152 Mbit/s | 仅 +14.5% |

ATF 是 airtime 公平，不是吞吐公平；权重 16:1 只能换来约 +14.5%，且受链路速率/TCP 影响很大。

### 方案 C1：AC 策略（VIP 走 VO，普通走 BE）

用 `SO_PRIORITY=262`（VO）和 `256`（BE）各发一路 UDP 下行，默认 EDCA，3 s：

| 流 | 吞吐 |
|---|---|
| VO（VIP） | **99.7 Mbit/s** |
| BE（普通） | **36.3 Mbit/s** |

**VO:BE ≈ 2.75:1**，且这是零内核改动的标准 EDCA 行为；EDCA 参数切换的业务可见时间约 0.1–0.3 s，命令→固件 ACK 约 0.26–0.30 ms。

## 方案矩阵

| 方案 | 层面 | VIP 强度 | 粒度 | 风险 | 工作量 | 依赖 |
|---|---|---|---|---|---|---|
| A | mac80211 airtime_weight | 弱（+14.5%） | per-STA | 低 | 小 | 标准 nl80211 |
| B | mt7996 固件 per-WCID | 强（预期） | per-STA | **高** | 大 | MTK 固件接口/文档 |
| C1 | AC 策略（VO/BE） | 强（2.75:1） | per-AC/per-flow | **低** | 小 | 分类规则 |
| C2 | 频段隔离（VIP 5G / 普通 2.4G） | 强（隔离） | per-band | 低 | 小 | 双频/双 SSID |
| C3 | mt76 host per-WCID token bucket | 强/可调 | per-STA | **中** | 中 | 驱动 patch，无固件依赖 |
| C4 | C1 + C3 | 最强 | per-STA + AC | 中 | 中 | 组合 |

## 推荐：C1 先落地，C3 做中期，B 只做备选

### 为什么不是 B

- B 要动 mt7996 固件/WCID 调度，需要 MTK 固件接口或文档；目前没有可用的 per-WCID 权重 API；
- mt76 的 TX 调度实际调用 mac80211 `ieee80211_next_txq()`，固件层再加权重容易和主机调度冲突；
- 失败成本高，且难以定位是主机还是固件的问题。

### 为什么 C1 先落地

- 零内核改动，今天就能用；
- 实测 VO:BE = 2.75:1，VIP 效果明显；
- 适合“VIP 明显更快”的验收口径；
- 风险是 VO 严格优先，普通流量可能被压得很低；可以用 VI 代替 VO，或给 VIP 加 policer 限制其上限。

### 为什么 C3 是中期最优

- 在 mt76 host 侧给每个 WCID 做字节 token bucket，权重直接控制“发多少字节”，不受链路速率影响；
- 仍然走 mac80211 `ieee80211_next_txq()`，不需要固件接口；
- 比 A 强（字节配额 vs airtime），比 B 风险低（不碰固件）；
- 可实现 1:2、1:4 等可配置比例，并给普通 STA 保底，避免饿死。

## C3 的实现草案

```c
struct mt76_wcid {
    ...
    u32 tx_weight;      /* 1..N，默认 1 */
    s32 tx_tokens;      /* 字节 token，可为负 */
};

/* mt76_txq_schedule_list() 内，取到 txq 后 */
wcid = rcu_dereference(dev->wcid[mtxq->wcid]);
if (!mt76_wcid_token_ok(wcid)) {
    ieee80211_return_txq(phy->hw, txq, false);
    continue;
}
/* 发送后按字节扣 token；每 10 ms 按 weight 补充 */
```

- 权重通过 debugfs 按 MAC 配置：`/sys/kernel/debug/ieee80211/phy0/mt76/sta_weight`；
- 默认 weight=1，所有 STA 等权；VIP 设 4，普通设 1；
- token 补充周期 10 ms，`tokens += weight * QUANTUM`；
- 需要处理 BA/聚合、PS、offchannel，避免 token 为负时长期跳过导致断流；
- 建议先做 1:4 两 STA UDP 饱和测试，再上 TCP。

## 实施顺序

1. **C1（1–2 天）**：在 AP 侧用 nft/tc 给 VIP 目的 IP/MAC 打 DSCP EF（或应用侧 SO_PRIORITY=262），普通 BE；验证 2–3x 与普通保底；
2. **C3（1–2 周）**：mt76 host per-WCID token bucket，debugfs 配权重；两 STA 饱和测试 1:2/1:4；
3. **C4**：C1 保证时延/优先级，C3 保证吞吐比例；
4. **B**：仅当 C3 被固件调度完全覆盖、且 MTK 提供 per-WCID 权重接口时再做。

## 结论

**最优性价比是 C1 + C3 的组合，而不是直接上 B。**

- 要“马上看到 VIP 效果”：C1，实测 2.75:1；
- 要“可配置比例、精细 per-STA”：C3，风险中等、无固件依赖；
- B 效果上限最高，但风险/成本也最高，只在 C3 证明不够时再上。
