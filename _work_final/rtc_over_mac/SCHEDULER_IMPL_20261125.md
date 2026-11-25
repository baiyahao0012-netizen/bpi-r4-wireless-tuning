# 调度器实现（quota 入队 / ai-first 出队，2026-11-25）

## 1. 语义（与 contrib/genai 对齐）

- **quota**（`QuotaWifiQueueScheduler::HasToDropBeforeEnqueue`）：队满时，若到达流自身字节 < 份额则驱逐"超额最多"流的队首并接纳，否则拒绝；份额 = `max(MinPerFlow×1484, 容量包数×1484/活跃流数)`；服务顺序 FCFS。
- **ai-first**（`AiFirstWifiQueueScheduler::GetPriority`）：AI 流优先，同类内按入队时间 FCFS；只排序不驱逐。

## 2. 实现位置与保真度

- 实现在**下行发送端的应用队列**（`tools/l2_ai_sched.py`，服务端 `l2_ai_server.py` 集成）；
- AP 内核 TC 对照已证伪（HTB 在驱动 FIFO 之前，改不了 MAC 内顺序），因此定位为 **A 档：应用层等价实现**；
- 前提：令牌桶限速使该队列成为瓶颈（`--rate-mbps`）；`sendp` 开销用账本 `sendp_us` 扣除。

## 3. 埋点（按审计修正）

| 计数器 | 含义 |
|---|---|
| `evicted_by_flow` / `rejected_by_flow` | 拆分驱逐/拒绝（原 `dropped` 混记） |
| `ai_overtakes` | **收窄定义**：AI 帧被发送时，队列中"入队早于它"的 bulk 帧数（不是"队列非空"） |
| `fcfs_violations` | 同流相邻服务中入队时间反转次数 |
| `service_order` | 最近 256 条 (t, flow, enq_ns) |
| `sendp_calls` / `attempts_total` | 真实 sendp 次数 / 含注入的尝试总数 |
| `msg_done/abandoned/rejected` | 消息级终态 |

`peek→pop` 取代"弹出再回插"，消除令牌不足导致的同流乱序（fcfs 6→3）。

## 4. 结果（Wi-Fi 下行，bulk 40 Mbps offered，限速 10 Mbps，AI 10 次/秒，12 s）

| 臂 | 容量 | 送达 | TTFT p50 | p95 | ai_overtakes | fcfs_viol | AI 被拒 |
|---|---:|---:|---:|---:|---:|---:|---:|
| S1b fifo | 500 | 71/80 | **989 ms** | 2069 ms | 0 | 7 | 342 |
| S3b ai-first | 500 | 79/80 | **31.2 ms** | 185 ms | 40,803 | 6 | 188 |
| S3c ai-first | **15** | 79/80 | **30.2 ms** | 282 ms | 21 | 6 | 260 |
| S3d ai-first（peek 修复） | 500 | 80/80 | **37.5 ms** | 297 ms | 36,749 | **3** | 214 |

关键点：

1. **ai-first 的收益不是深队列假象**：容量压到 15（≈AQL 在途量级）时 p50 仍为 30 ms，与 500 时同量级；
2. `ai_overtakes>0` 且为"早于 AI 入队的 bulk 数"，是真正的越队证据；
3. fifo 下 `ai_overtakes=0`（对照成立）。

## 5. 未完成

- S2（quota 驱逐）、S5（超份额负向）、S6（限速≥链路容量的对照）尚未跑；
- fcfs_violations 仍有 3（~0.04%），需定位来源；
- 结论口径：所有数字来自应用层队列，**不能外推为 MAC 队列行为**。

## 6. 第二轮审计修正（度量口径）

| 审计项 | 修正 | 验证 |
|---|---|---|
| `attempts_total` 反而小于 `sendp_calls` | 改为 `attempts_ever`（每次发送/注入都 +1）；另报 `attempts_ledger=Σlen(sends)` 与 `attempts_ge_sendp` 自检 | S1f `attempts=128 = sendp=128`、`ge=True`；`ledger=112`（16 条已淘汰，可解释） |
| `fcfs_violations` 不可用（fifo 报 7） | 删除"相邻比较"，改为**服务结束后按 flow 扫全量 service_log 检查 enq 单调**；顺带修根因：重试复用旧 Item 导致 enq_ns 早于后入队项（重试时新建 Item） | S1f fifo `fcfs_inv=0`、S3f ai-first `fcfs_inv=0` |
| `ai_overtakes` 是帧数不是次数 | 拆成 `ai_jump_frames`（发生越队的 AI 条数）与 `bulk_skipped_total`（被跳过的 bulk 帧数） | S3f `jump=92`、`skipped=44590`；S1f 两者均 0 |
| quota 在 capacity 15 下数学退化 | 加 `quota_degenerate` 标志（`min_per_flow > capacity` 时置真）；quota 一律在 capacity 500 跑 | S2e cap500 `degen=False`、`evict=138`、`evicted_by_flow={1:42,2:39,3:33,4:24}` |

### 6.1 修正后的主表

| 臂 | 送达 | TTFT p50 | p95 | jump | fcfs_inv |
|---|---:|---:|---:|---:|---:|
| S1f fifo（cap500） | 70/80 | 1051.6 ms | 2078.8 ms | 0 | 0 |
| S3f ai-first（cap500） | **80/80** | **50.8 ms** | 180.2 ms | 92 | 0 |
| S2e quota（cap500） | 68/80 | 983.6 ms | 1074.7 ms | 0 | 0 |

- ai-first 相对 fifo：p50 约 **20×** 改善，且每次 AI 发送都确实越过了更早入队的 bulk（jump=92）；
- quota 单独不改善时延（保护准入、保持 FCFS），与仿真语义一致；
- 所有结论仅限应用层队列。

## 7. 仍未完成

- S5（quota 负向：AI 自身超过份额时应被拒）；
- S6（`rate ≥ 250 Mbps` 对照：无积压时 ai-first 应无收益）；
- S2 的"受害者是超标最多流"需按 `evicted_by_flow` 与当时的每流字节对账（账本已记录 sends 与时间，可离线重算）。

## 8. S5 负向与 S6 对照（2026-11-25）

### 8.1 S5：AI 自身超过份额时应被拒（通过）

配置：quota、cap500、rate 0.05 Mbps、bulk 0.2 Mbps、AI 30 次/秒、12 s。

| 计数器 | 值 |
|---|---:|
| `rejected_by_flow` | `{0: 4838, 1: 95}` |
| `evicted_by_flow` | `{0: 27}` |
| `retry_rejected` | 4,820 |
| `msg_done` | 6 / 364 |

结论：AI 自身字节超过份额后，到达帧被拒绝，且驱逐受害者正是"最超额"的 AI 流——保护不是无条件的，规则与仿真一致。送达崩溃（15/364）是负向实验的预期结果。

### 8.2 S6：rate ≥ 链路容量对照（失败，原因重要）

配置：rate 250 Mbps、bulk 40 Mbps、cap500，ai-first 与 fifo 各一轮。

| 臂 | 送达 | TTFT p50 | p95 | 队列深度 | bulk 实际 |
|---|---:|---:|---:|---:|---:|
| S6a ai-first | 80/80 | 68.8 ms | 376 ms | 500 | ~9.8 Mbps |
| S6b fifo | 64/80 | 1383 ms | 2724 ms | 500 | ~7.2 Mbps |

**预期**：rate 提高后无积压，ai-first 应失效。**实际**：队列仍满。

原因：`sendp` 本身把排空速率限制在 **~7–10 Mbps**（约 900 pps × 1400 B，每帧 ~12 ms），提高令牌桶上限不起作用——**发送端成为新的瓶颈**，队列无法被排空。因此 S6 不能作为"无积压"对照；要得到有效对照，必须换快速发送端（C/Npcap）或直接限制批量源。

这也解释了 S1f/S3f：两臂都在发送端上限附近，队列恒满。

结论口径：调度器的结论只在"应用层队列是瓶颈"时成立；本机 `sendp` 上限（~10 Mbps）使这一点始终成立，因此**无法用当前工具链验证"瓶颈移走则收益消失"**。
