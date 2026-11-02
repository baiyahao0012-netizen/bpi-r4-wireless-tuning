# 工具包分析：`backports-src.rar`（对方 2026-11-02 发来）

分析日期：2026-11-02  
来源：用户转发的 `backports-src.rar`（14,060,339 B，sha256 `38d0a35e…`）  
解包后落盘：[`_work_merge/other_src/`](<_work_merge/other_src/>)（2,894 个文件，69 MB）

---

## 0. 结论：**这正是之前缺的那块拼图**

上一轮分析的结论是「**只拿到对方的二进制，没有源码，无法合并 mac80211 补丁**」。
这个包把缺的东西**全部补齐了**：

| 之前缺的 | 现在有了 |
|---|---|
| mac80211 `wifi_dscp` 埋点**源码** | ✅ `354-wifi-mac80211-add-dscp-latency-tracepoint.patch`（393 行 / 16 hunk / 5 文件） |
| mt76 重传上报**源码** | ✅ `355-wifi-mt76-mt7996-report-tx-retries.patch`（1 hunk） |
| 对方改动过的 backports **参考源码树** | ✅ `backports-6.12.96/`（已打补丁，可直接对照/diff） |
| 用户态统计工具 | ✅ `dscpstats` + `dscpstats.awk` |
| 设计/使用文档 | ✅ `README.md`（859 行）+ `REQUIREMENTS.md`（376 行） |
| 软件自测用例 | ✅ `test/`（L2 golden + L3 管线仿真） |

**一句话：合并 mac80211 的技术障碍已经消除，现在只剩「选基线 + 编一次」的工程量。**

---

## 1. 包内容清单（已核验 sha256）

```text
文件                                         大小         sha256(前16)
354-wifi-mac80211-add-dscp-latency-…patch   12,261 B    260455b9757a6fc9   ← mac80211 埋点（权威副本）
355-wifi-mt76-mt7996-report-tx-retries…     587 B     a4f6987f04de6eb1   ← mt76 重传上报
README.md                                   44,840 B    f8961ef19f2376ad   ← 总文档（改了什么/怎么编/怎么部署/用户手册）
REQUIREMENTS.md                             19,514 B    1306d9dcfdc7a8ce   ← 需求设计 + 实测明细
dscpstats                                    7,656 B    581db45894d48156   ← 用户态入口脚本
dscpstats.awk                                2,656 B    63de6a4d04be8d22   ← 聚合器
backports-6.12.96/                          69 MB       —                   ← 已打补丁的参考源码树
test/                                        ~11 KB      —                   ← 纯软件自测
```

参考树版本标记（`backports-6.12.96/versions`）：
```text
BACKPORTS_VERSION="d43b2b8"
BACKPORTED_KERNEL_VERSION="v6.12.96-0-g6d15a1029"
```
与 `REQUIREMENTS.md` §9 的核对结果一致，可信。

---

## 2. 核心资产 1：mac80211 DSCP 埋点补丁 `354-*`

**只改 5 个已存在文件、16 个 hunk，不新增文件、不改 Makefile。**

| 文件 | 改了什么 | hunk |
|---|---|---|
| `net/mac80211/ieee80211_i.h` | 加 2 个头；新增 `enum wifi_dscp_dir`/`wifi_dscp_stage`；3 个 `static inline`（`_match` / `_eth` / `_80211`） | 2 |
| `net/mac80211/trace.h` | 文件末尾新增 `TRACE_EVENT(wifi_dscp, …)` | 1 |
| `net/mac80211/tx.c` | `ieee80211_txq_enqueue()` 打 **ENQ**；`ieee80211_tx_dequeue()` 打 **DEQ** | 3 |
| `net/mac80211/status.c` | `ieee80211_report_used_skb()` 打 **ACK**；连带 6 处调用点补 `retry_count` 形参 | 7 |
| `net/mac80211/rx.c` | `ieee80211_rx_h_data()`（慢路兜底）+ `ieee80211_rx_8023()`（fast-rx/decap-offload 真实入口）打 **RX** | 3 |

**事件模型（设计得很干净，正好能给我们用）：**

```
TRACE_EVENT(wifi_dscp, dir, stage, dscp, len, skb, ts, acked, retry)
  dir   0=TX 1=RX
  stage 0=ENQ 1=DEQ 2=ACK 3=RX
  skb   关联 TX 三阶段的 key
```

- **只统计 8 个目标 DSCP**（`tos & 0xfc` 命中才发事件，其余不产生事件、不占 trace 带宽）：
  `0x88 AF41`、`0xa0 CS5`、`0x80 CS4`、`0x68 AF31`、`0x48 AF21`、`0x30 AF12`、`0x28 AF11`、**`0x20 CS1`**
- **`0x20 CS1` 就在列表里** —— 这正是我们 OAF（`mark=1900`）→ DSCP → BK 那条链路要观察的档位。
- 时延：`queue = ENQ→DEQ`、`access = DEQ→ACK`、`e2e = ENQ→ACK`，单位 us，全部在内核侧取 `ktime_get_ns()`。
- 单开关：`events/mac80211/wifi_dscp/enable`。

**两个关键的工程细节（他们踩过的坑，我们直接受益）：**

1. 本平台数据面走 **802.3 HW-encap**（`IEEE80211_TX_CTL_HW_80211_ENCAP`），ENQ/DEQ 时 skb 是**以太帧**而不是 802.11 帧，所以解析器要按标志二选一。
2. RX data 帧走 **decap-offload / fast-rx**（`SUPPORTS_RX_DECAP_OFFLOAD`），**绕过** `ieee80211_rx_h_data()`，必须在 `ieee80211_rx_8023()` 补埋点，否则一条 RX 事件都收不到。

---

## 3. 核心资产 2：mt76 重传上报补丁 `355-*`

只有 1 个 hunk，改 `mt7996/mac.c` 的 `mt7996_mac_add_txs_skb()`：

```c
-  info->status.rates[0].idx = -1;
+  info->status.rates[0].idx = 0;
+  info->status.rates[0].count =
+      FIELD_GET(MT_TXS5_F0_TX_COUNT, txs_data[5]);
```

原因：mt7996 不往 mac80211 填 legacy `status.rates[].count`，导致 mac80211 算出的 `retry_count` 恒为 0。
**不打这个补丁，重传率永远是 0。**

---

## 4. 核心资产 3：`dscpstats` 用户态工具

- `dscpstats start|stop|status|help`：找 tracefs → 起 `cat trace_pipe` + `awk` 后台聚合 → 开关 `wifi_dscp/enable`。
- `dscpstats.awk`：按 `skb` 关联同一包的 ENQ/DEQ/ACK，算 queue/access/e2e 的 avg/min/max，以及 `retryP/reAvg/reMax/re%`；约每秒原子写 `/tmp/dscpstats.state`（22 列）。
- 只依赖 tracefs + `awk`，**无额外依赖**，可直接放进我们的 overlay。

---

## 5. 版本核对（合并的关键约束）

| 项 | 我方（板子实测 / 仓库） | 对方（镜像 / 文档） |
|---|---|---|
| OpenWrt | 24.10.0 `r28427-6df0e3d02a`（2025-02） | `v24.10.8-17-ga1ea57bd05`（2026-08-12） |
| 内核 | **6.6.73** | **6.6.151** |
| mac80211 / backports | **6.12.6**（`kmod-mac80211 6.6.73.6.12.6-r1`） | **6.12.96**（`BACKPORTS_VERSION=d43b2b8`） |
| mt76 | `2025.01.14~8e4f72b6` | `2025.11.06~eb567bc7` |
| 构建环境 | SDK 24.10.0（[`_sdk/openwrt-sdk.tar.zst`](<_sdk/openwrt-sdk.tar.zst>)，有） | 完整 buildroot `/home/sean/openwrt_mod/openwrt`（**没有**） |
| mac80211.ko 大小 | 6,603,848 B | 8,358,768 B |

> mac80211.ko 差了 1.75 MB —— 主要不是补丁，而是对方开了
> **`CONFIG_PACKAGE_MAC80211_TRACING=y`**（所有 `drv_*` tracepoint 都编进去了），我方没开。
> **要合并就必须把这个配置打开。**

---

## 6. 移植可行性（已实测，结论乐观）

补丁锚定的函数在我方 6.12.6 的 `mac80211.ko` 里**全部存在**：

```text
ieee80211_handle_teardown_ttlm_status   present   ← status.c 的上下文锚点
drv_neg_ttlm_res                        present   ← trace.h 的上下文锚点
ieee80211_rx_8023                       present   ← RX 埋点位置
ieee80211_rx_h_data / txq_enqueue / report_used_skb   present
fq_weight                               present   ← 我们的 WDRR 已在跑
wifi_dscp                               ABSENT    ← 正是要加进去的
```

**结论：`354` 应该能应用到 6.12.6，最坏情况是小幅行号偏移或个别 hunk 手工落位。**
（我方 backports 6.12.6 与对方 6.12.96 都含 TTLM，说明两者同属一个较新的无线栈世代，差异比想象中小。）

**唯一需要动手合并的地方**：`354` 的 DEQ 埋点和我们的 **WDRR 补丁都改 `tx.c` 的 `ieee80211_tx_dequeue()`**
（WDRR 改 `cstats = &txqi->cstats;` 之后，DEQ 埋点改 `spin_unlock_bh(&fq->lock);` 之后）。
两处插入点不同、不冲突，但要在同一棵树上按顺序落位。其余文件（`fq.h`/`fq_impl.h` vs `trace.h`/`status.c`/`rx.c`）完全不相干。

---

## 7. 更新后的合并方案（推荐：以我方 24.10.0 为基线）

上一轮我倾向「方案 A：以对方 6.6.151 为基线」。**拿到这个包之后，推荐改为方案 B**，
因为对方的补丁已经小到可以移植，而对方的 buildroot 我们拿不到：

```text
第 1 步  备好 24.10.0 构建环境（SDK 已有；确认能取到 backports-6.12.6 源码）
第 2 步  打开 CONFIG_PACKAGE_MAC80211_TRACING=y
第 3 步  在 backports-6.12.6 上先试 patch -p1 --dry-run 应用 354（记录偏移/fuzz）
第 4 步  同一棵树上再应用我们的 WDRR（apply_wdrr.py）—— tx.c 两处插入点手工合并
第 5 步  编 kmod-mac80211，验证两个功能同时存在：
           ls /sys/module/mac80211/parameters/fq_weight          ← WDRR
           ls /sys/kernel/debug/tracing/events/mac80211/wifi_dscp ← DSCP
第 6 步  在 mt76 2025.01.14~8e4f72b6 的 mt7996/mac.c 上落 355 的 1 个 hunk，
         与我们的 EDCA/A-MPDU 补丁一起编 mt7996e.ko
第 7 步  部署 mac80211.ko + mt7996e.ko + dscpstats，重启（切勿 rmmod mt7996e）
第 8 步  联调验证：OAF mark=1900 → CS1(0x20) → BK，用 dscpstats 量 queue/access/e2e 与重传率
```

**这套方案的价值**：对方的 DSCP 埋点正好能把我们 OAF/EDCA/BK 的效果**按 DSCP 档位量化**——
包括 `0x20 CS1`（背景流量）和 `0x88 AF41`（视频）在同一时刻的 queue/access/e2e 对比，
以及开/关 BK 激进参数时的重传率变化。这是之前 A/B 网页测试给不出的粒度。

---

## 8. 仍未拿到 / 需要确认

1. **对方的 OpenWrt buildroot**（`/home/sean/openwrt_mod/openwrt`）——只有改用对方 24.10.8 基线时才需要；
   走方案 B 不需要。
2. **对方的 mt76 包源码树** ——不需要，`355` 只有 1 个 hunk，且我们知道目标函数。
3. **基线决策**：24.10.0（我方，推荐）还是 24.10.8 + 6.6.151（对方）？
4. 对方 `REQUIREMENTS.md` 提到一个更早的固件
   `ImmortalWrt_BPI-R4_wifi_delay_sdcard.img`（内含自定义 raw tracepoint `wifi_delay`），
   他们**没有逆向**、自行实现了 `wifi_dscp`。这个 `wifi_delay` 固件是谁做的、还要不要，
   值得确认一下（可能就是你说的「硬件部分」那个来源）。

---

## 9. 风险提示

| 风险 | 说明 | 应对 |
|---|---|---|
| 补丁偏移 | 6.12.96 → 6.12.6 行号/上下文差异 | 先 `--dry-run`，按函数名定位手工落位 |
| 开启 TRACING 的连锁 | `MAC80211_TRACING` 会改变 mac80211 编译产物 | mac80211 与 mt76 一起重编，保持配置一致 |
| trace 开销 | ACK 事件对所有 data 帧都发，高包量下 awk 可能跟不上 | 只开必要阶段；短窗口测量 |
| A-MPDU 下 retry 口径 | mac80211 对 `AMPDU && !STAT_AMPDU` 强制 `retry=0` | 重传率测试在非聚合场景做，或后续另立口径 |
| 热重载崩固件 | `rmmod mt7996e` 会把 MT7996 MCU 打崩 | 一律「换文件 + 重启」 |
