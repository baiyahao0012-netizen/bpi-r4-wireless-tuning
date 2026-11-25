# 反馈机制实现（对齐仿真语义，2026-11-25）

目标：把 `contrib/genai` 的反馈机制在真机上实现成与仿真**语义一致**的状态机，并用机制级计数器验证。

## 1. 与仿真的对照

| 仿真语义 | 实现 |
|---|---|
| `Store`(`ai-server-application.cc:347`) 先于发送(`:352`) | 请求一到即建 `rec{state:"queued", attempts:0, item}`，**登记在入队之前** |
| 入队被拒 → `DropBeforeEnqueue` → 立即补发 | `enqueue()` 返回值被接住；失败置 `rejected` 并计数 `enqueue_reject`，由重试回路补发 |
| 发送失败 → 补发 | `send_err` 不再跳过，回置 `queued` 并计数 `send_err_retry` |
| 去重 = 只推理一次，但可重复传输 | 重复请求且 `state != done` → **重发响应**（`resp_dup_resend`）；仅 `done` 时只回 ACK |
| 重发上限 8（`kMaxResendsPerChunk`/`kMaxRequestRetxAttempts`） | `attempts < max_resend` 对所有路径生效（含 dup），超出计 `resend_cap_hit` |
| 事件驱动补发 | 入队拒绝/发送失败为事件驱动（≈0 ms） |
| MAC 丢包事件 | 真机不可得 → 用**响应超时**（默认 80 ms）作为等价信号（`retx_timeout`） |

状态机：`queued → inflight → done`，任一非 `done` 态的失败都回到 `queued`。

客户端补充：等响应超时（仅当请求尚未被 ACK）→ 重发请求，指数退避，计 `resp_timeout_resend`。

工程修正：服务端 ACK 从抓包线程移到独立 `ack_loop`，避免 `sendp` 阻塞导致 Npcap 漏收（此前造成过一次"重传风暴→漏收→17%"的回归）。

## 2. 结果

场景：100 个请求，服务端注入 40% ACK 丢失 + 40% 响应丢失。

| 实现 | 送达 | 说明 |
|---|---|---|
| 旧（登记在发送后、dup 直接 return） | 84/100 | 响应丢失后无可查记录，dup 请求被吞 |
| **新（三态 + 登记前置 + dup 重发）** | **100/100** | 见 `evidence/feedback_20261125/server_drops3.json` |

服务端机制计数器（同一轮）：

| 计数器 | 值 | 含义 |
|---|---:|---|
| requests_rx | 237 | 100 唯一 + 137 重复 |
| requests_dup | 137 | 去重路径命中 |
| resp_dup_resend | 57 | dup 黑洞已补（旧实现此处为 0） |
| retx_timeout | 36 | 超时驱动的空中丢失恢复 |
| resp_lost | 80 | 注入的响应丢失 |
| ack_dropped | 110 | 注入的 ACK 丢失 |
| responses_sent | 113 | **> 唯一请求 100**：一次推理、多次传输 |
| done | 113 | ACK 确认完成 |
| resend_cap_hit | 0 | 未触上限 |

单记录发送次数：最大 **4**、中位 **1**（≤ 8 上限）。

## 3. 保真度缺口（写进报告）

1. **无 MAC 层 ACK**：0x88B8 是"L4 代 MAC"，mac80211 的 BlockAck 对应用不可见；
2. **空口丢包只能靠超时**（80 ms 级）发现，仿真的 `DroppedMpdu` 是立即触发——事件粒度差一层；
3. 因此时延分两档：事件驱动 ≈ 0 ms，超时驱动 ≈ 80 ms；TTFT 的 p95 主要来自后者。

## 4. 环境记录（影响后续实验）

- AP 对 MT7921AU 的 `tx failed` 约 **12%**（实测 138/1123），这是真实空口丢帧，不是软件问题；
- 板载 Wi-Fi 已在 `/boot/firmware/config.txt` 加 `dtoverlay=disable-wifi`（**需重启生效**），避免同机自干扰与周期性扫描尖刺；
- 重启后 NetworkManager 会把 wlan1 连到 `DianGroup103`，跑实验前必须先 `nmcli connection up rtc-media ifname wlan1` 切回 `BPI-R4-5G`；
- 目前只有一个 USB 无线网卡（`0e8d:7961`），第二 STA 实验需再插一个 dongle。

## 5. 复现

```bash
# 服务端（笔记本，需 Npcap）
python tools/l2_ai_server.py --mode fifo --seconds 18 --bulk-mbps 0 \
  --ack-drop 0.4 --resp-drop 0.4 --resp-timeout-ms 80 --out srv.json --csv srv.csv

# 客户端（Pi）
sudo python3 tools/l2_ai_client.py --dst-mac 40:c2:ba:52:70:95 \
  --seconds 10 --msg-base 80000 --resp-timeout-ms 120 --out cli.json
```

## 6. 稳定性检测与零点（2026-11-25 14:00）

### 6.1 硬件事件

- USB 网卡（MT7921AU）在重启后重枚举为 `wlan0`，期间出现多次 `USB disconnect` / `reset high-speed`，导致静态 IP 丢失、三次基线作废（39/100、80/100）；
- 现直插 Bus001 Port002（根 hub、High Speed 480M），探测期间无新断连；
- 设备本身是 USB 2.0（`bcdUSB 2.10`、`MaxPower 100mA`），换 3.0 口不会提速。

### 6.2 稳定化措施

- 板载 Wi-Fi 已禁用（`dtoverlay=disable-wifi`，重启生效）；
- **关闭省电**：`iw dev wlan0 set power_save off`（preflight 会检查，on 则 FAIL）；
- 客户端重传全部加指数退避（请求 ACK 与响应等待两路），避免重传风暴。

### 6.3 稳定性结果

| 项 | 关省电前 | 关省电后 |
|---|---:|---:|
| idle ping 丢包 | 0/150 | 0/150 |
| idle avg / max / mdev | 8.7 / 116.5 / 21.5 ms | **4.2 / 62.8 / 8.8 ms** |
| 负载期 ping（100M UDP 下行） | — | 0/100，avg 2.4 / max 25.8 ms |
| AP→Pi 吞吐 | — | 100M offered → 95.3 Mbps (4.7% 丢)；200M → 179 Mbps (11% 丢) |

### 6.4 干净基线（无注入、无 bulk，10 s × 3 次）

| 轮次 | 请求 | 送达 | TTFT p50 | TTFT p95 | 请求重传 |
|---|---:|---:|---:|---:|---:|
| clean1 | 100 | 100 | 16.0 ms | 44.9 ms | 28 |
| clean2 | 100 | 100 | 25.5 ms | 144.0 ms | 38 |
| clean3 | 100 | 100 | 15.5 ms | 49.1 ms | 36 |

- 送达稳定 100/100；
- p50 稳定在 15–26 ms；p95 45–144 ms；
- 服务端内部 recv→send p50 = 0 µs，p95 约 15–46 ms → 剩余时延主要来自 Windows/Npcap 发送路径与空口，不是协议逻辑；
- 与 ping 的 4.2 ms 相比，p50 16 ms 的差额有待用"AP 侧发送时间戳"进一步拆分（下一步）。

## 7. 埋点与定点注入（2026-11-25 下午）

### 7.1 新增能力

- **逐消息账本**：`--ledger` 输出 JSONL，服务端字段 `constructed / dup_requests / injected_drop / sends[{n,t,ack,sendp_us,injected}]`；客户端字段 `t0/attempts/reasons/ttft/dup_resp/resp_from_attempt`；
- **ACK 三态**：`ack: none|recv|timeout`（不再写"丢"，"丢"是推断）；
- **响应携带 attempt**：`flags` 字段回传第几次发送，客户端据此记录 `resp_from_attempt`；
- **进程内定点注入**：`--drop-resp mid:n`（假装发出但丢失→超时档）、`--fail-resp mid:n`（立即失败→事件档）、`--drop-ack-req mid:n`、`--drop-req mid:n`、`--fail-req mid:n`、`--drop-ack-resp mid:n`；
- **echo 探针 `0x88B9`**：已实现但**判定不可用**——回复走 scapy `sendp`，每次 20–40 ms，20 个探针自激排队（空闲 p50 380 ms），不能当空口底噪。

### 7.2 已测结果

| 实验 | 结果 |
|---|---|
| **E0 有线对照** | 80/80 送达，**TTFT p50 13.1 ms**、p95 36.8 ms → 工具底噪（Npcap+Python）就有 13 ms |
| E1 WiFi | 100/100 送达，**TTFT p50 16.4 ms**、p95 55.0 ms → 空口只多约 3 ms |
| E2 超时档 | mid 500000 账本：`n=1 injected:"drop"`、`n=2 ack:"recv"`；但该轮恢复走的是 dup 路径（客户端重发请求），需用大 ack-timeout 隔离 |
| **E9 事件档** | mid 500000 账本：`n=1 injected:"fail"`、**`n=2` 与 `n=1` 同一时间戳**（≈0 ms 补发），`send_err_retry=1`，40/40 送达 |

### 7.3 发现的放大器问题

用 runner 跑 E1（60 请求 / 6 s）时出现 0 送达、`requests_rx=578`（9.6 倍放大）：客户端因 ACK 超时重发请求，服务端**每个 dup 都重发一次响应**，两者叠加形成风暴，最终客户端收不到任何响应。修法（下一步）：dup 重发加最小间隔（如 `resp_timeout/2`）或只在"从未发出"时才补发。

## 8. 定点注入矩阵结果（2026-11-25 下午）

参数统一：40 请求/4 s，`--ledger` 开启；时间档测试把客户端 ack-timeout 设为 5000 ms 以隔离。

| 实验 | 注入 | 服务端账本（目标 mid） | 客户端 | 结论 |
|---|---|---|---|---|
| E2 | 响应第 1 次不发 | `n=1 injected:drop(ack:timeout)` → `n=2 recv, ack_after=78ms` | 40/40 | 超时档：约 80 ms 后补发 |
| E3 | 连续 4 次不发 | `n=1..4 drop` → `n=5 recv` | 40/40 | 多次超时后恢复 |
| E4 | 连续 9 次不发 | `n=1..8 drop`，`final:inflight` | 39/40 | 8 次上限生效，该条放弃 |
| E5 | 请求 ACK 丢 2 次 | `constructed=40`（=唯一请求），`requests_dup=25` | 40/40 | **去重=只推理一次**，dup 不重复构造 |
| E6 | 响应 ACK 丢 1 次 | `retx_timeout=10`，`responses_sent=50` | 40/40，`dup_resp=10` | 重复响应不重复计数 |

### 8.1 仍未闭合的两项

- **E8（请求首发不发）**：客户端正确重传（`injected_drop=1`），但负载下服务端 `max_queue_depth=21`、`ack_resp_recv=34/112`，送达 25/40。说明**基于定时器的请求重传在丢包叠加时会过触发**（仿真用的是 MAC 丢包事件，不是超时），反馈环路仍会自激。
- **E10（队列拒绝）**：客户端进程未产生结果（stderr 被 runner 丢弃），需单独重跑。

### 8.2 与仿真的差异（已确认）

| 仿真 | 真机 | 影响 |
|---|---|---|
| 重发由 `DroppedMpdu`/`DropBeforeEnqueue` 触发（事件，≈0 ms） | 事件只能覆盖"入队拒绝/发送失败"；空中丢包只能靠 **ACK 超时** | 超时档 78 ms；定时器在延迟抖动下会过触发（E8 的自激） |
| 每次丢包才重发 | 定时器到期就重发 | 需要 RTT 自适应超时 + 每秒重发上限 |

下一步修法：客户端 ack-timeout 改为 **RTT 自适应**（`max(150ms, 3×ack_rtt_p95)`）+ 全局重发速率上限，然后重跑 E8/E10。
