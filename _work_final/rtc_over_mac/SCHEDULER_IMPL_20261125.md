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

## 9. S6 用快速发送端补齐（通过）

新增 `tools/fast_tx.py`：用 Npcap `pcap_sendpacket`（ctypes）替代 scapy `sendp`，实测调用速率 ~300k pps，服务端 `--fast-tx` 启用。

关键修正：1400 B 自定义 L2 帧的**空口实际吞吐只有 ~37 Mbps**（与 iperf3 UDP 的 197 Mbps 不同，帧型/聚合不同）。所以 S6 要"无积压"，bulk 必须低于 37 Mbps。

| 臂 | bulk | 队列深度 | ai_jump | TTFT p50 | p95 |
|---|---:|---:|---:|---:|---:|
| S6c ai-first | 40M（>空口 L2 上限） | 326 | 30 | 7.0 ms | 133.9 ms |
| S6d fifo | 40M | 392 | 0 | 27.6 ms | 150.6 ms |
| **S6g ai-first** | **10M（<上限）+ 1.5s warmup** | **88** | **0** | **10.6 ms** | 37.3 ms |
| **S6h fifo** | 10M + warmup | 68 | 0 | **12.0 ms** | 25.0 ms |

结论：有积压时 ai-first 明显（7.0 vs 27.6 ms）；无积压时收益消失（10.6 vs 12.0 ms，差 12% 属噪声）。**S6 对照成立**。

## 10. S4 组合模式与受害者核对

- S4（both，cap500，bulk40，rate10）：80/80 送达，p50 19.3 ms；`evict=60`、`evicted_by_flow={1:28,2:12,3:10,4:10}`、`ai_jump=86`、`fcfs_inv=0`。
- 受害者核对：给 `evict` 事件记录"当时份额 + 各流字节"，S2i 共 100 次驱逐，抽样 30 条**全部满足 `victim_over == max(flow_bytes) - share`**（例如 share=185500 时 `3:187600` 被选，超额 2100 为最大）。
- 修了一个日志格式 bug：detail 里的逗号会破坏 CSV 解析，改用 `;`。

## 11. 调度器阶段完成状态

| 实验 | 结论 |
|---|---|
| S1 fifo | 70/80，p50 1051 ms（基线） |
| S2 quota | `evict=138`，受害者=最超额流（已核对）；不改善时延（保护准入、保持 FCFS） |
| S3 ai-first | 80/80，p50 50.8 ms（cap500）/ 30.2 ms（cap15）；`ai_jump>0`、`fcfs_inv=0` |
| S4 both | 80/80，p50 19.3 ms；`evict=60` + `ai_jump=86` |
| S5 负向 | AI 超份额被拒（`rejected_by_flow[0]=4838`），受害者即最超额流 |
| S6 对照 | 无积压时收益消失（10.6 vs 12.0 ms，depth<90） |

限制（必须随报告）：全部结论来自**应用层队列**；空口 L2 帧上限 ~37 Mbps 与 iperf3 UDP 的 197 Mbps 不可混用；`sendp` 上限问题已由 `--fast-tx` 解决。

## 12. 口径统一与"深度-时延"散点（2026-11-25 晚）

### 12.1 确认主表混用了发送端

| 臂 | 发送端 | 实际 bulk | 深度 |
|---|---|---:|---:|
| S1f / S3f / S2e / S4 | scapy（~900 pps） | 4.8–5.6 Mbps | 500 |
| S6c / S6g | fast_tx（Npcap） | 40 / 9.1 Mbps | 326 / 88 |

因此 S1f 的 1051 ms 与 S4 的 19.3 ms **不可同表比较**。

### 12.2 笔记本路径的真实容量

200 Mbps offered、fast TX：`bulk_sent=64,875/14 s ≈ 52 Mbps`。所以"37 Mbps"是 40 Mbps 投放下的**接收量**（含 ~7% 丢包），不是路径上限；AP 本地发送（iperf3）≈197 Mbps——差异来自**路径**（笔记本→AP 桥转发 vs AP 本地协议栈），不是帧型。

### 12.3 同口径四臂（fast TX，bulk 30，cap500）

| 臂 | 送达 | TTFT p50 | depth@到达 p50 | Spearman(depth,ttft) |
|---|---:|---:|---:|---:|
| fifo | 80/80 | 157.1 ms | 381 | +0.53 |
| quota | 80/80 | 130.1 ms | 230 | +0.45 |
| ai-first | 80/80 | 8.2 ms | 2 | −0.34 |
| both | 80/80 | 9.5 ms | 0 | −0.14 |

注意：fifo 那轮 bulk 实际只有 22.9 Mbps（ai-first 30 Mbps），**链路漂移**混入了臂间差异；因此不能把 157/8.2 当纯调度效应。

### 12.4 交替重复（bulk 15，链路稳定）

| 轮次 | fifo | ai-first |
|---|---:|---:|
| I1 | 13.9 ms | 9.5 ms |
| I2 | 11.3 ms | 9.9 ms |

bulk 15 下所有臂 depth@到达 p50 ≈ 0–2，差距约 **1.3×**。

### 12.5 结论（替换"20×"）

**收益由"请求到达时的队列深度"决定**：深度大时（fifo 381）臂内相关系数 +0.53，TTFT 随深度上升；ai-first 把深度压到 2、TTFT 压到 8 ms。固定倍数依赖管道速率与队列深度，**"20×" 退役**，报告改用"深度-时延散点 + 不同 bulk 速率下的点"。

### 12.6 仍需

- 最终数字需**交替重复 3 次取中位**（单轮链路漂移已被证实）；
- 每轮记录 AP `tx bitrate/retries` 作为协变量；
- 散点需覆盖更多深度点（bulk 10/20/30/40 × 两模式）。

## 13. 曲线点（fast TX，cap500，单轮）

| bulk Mbps | fifo p50 | ai-first p50 | 比值 | fifo depth@到达 p50 | ai-first depth p50 |
|---:|---:|---:|---:|---:|---:|
| 10 | 28.9 ms | 10.7 ms | 2.7× | 24 | 2 |
| 15 | 13.9 / 11.3 ms | 9.5 / 9.9 ms | ~1.3× | ~0 | ~1 |
| 20 | 11.5 ms | 8.1 ms | 1.4× | 2 | 1 |
| 30 | 157–221 ms* | 7.8–8.2 ms | ~20×* | 381 | 2 |
| 40 | 13.9 ms | 6.4 ms | 2.2× | 4 | 7 |

\* bulk30 的 fifo 轮链路漂移（实际 22.9 Mbps），比值不可引用。

观察：

1. **比值随"是否形成深队列"跳变**，不是随 bulk 单调变化：深度浅（10/15/20/40 多数轮）时 1.3–2.7×；深度深（fifo 381）时 ~20×。
2. 单轮波动大（同 bulk 40，深度 p50 在两次实验里分别是 4 和 300+），**必须交替重复取中位**并记录 AP `tx bitrate/retries` 协变量。
3. 因此报告口径：**不写固定倍数**，写"深度-时延关系 + 各速率下的点"，并注明链路协变量未控制。

## 14. 本轮审计修正汇总

| 审计意见 | 处理 |
|---|---|
| 主表混用两种发送端 | 确认；同口径四臂已重跑（F_*），并标注 fifo 轮漂移 |
| 37 Mbps 归因 | 修正：笔记本路径 L2 容量 ~52 Mbps；197 Mbps 是 AP 本地发送，差异在**路径**不是帧型 |
| 10 Mbps 无积压但深度 68–88 | 那是整轮 max（启动瞬态）；按请求到达 p50 为 0–2；判据改为 `qdepth_at_recv` |
| depth 392 vs p50 27.6 矛盾 | 用逐请求深度解决：fifo 深队列轮 depth p50=381、Spearman +0.53 |
| "20×"退役 | 已退役；改为深度-时延散点 + 多速率点 |

## 15. 受控积压矩阵（最终口径，2026-11-25）

### 15.1 如何把"积压"变成构造条件

令令牌桶（5 Mbps）**低于** bulk 投放（10 Mbps）：队列必然被填满且在整轮内保持满。这样"队列是瓶颈"不再是偶发环境事件，而是实验设置。

协变量同步记录（`tools/covariates.sh`，每轮 before/after 各一行）：`tx_bitrate_mbps`、`signal_dbm`、`tx_retries`、`tx_failed`、`tx_packets`、`channel`、`txpower_dbm`。

### 15.2 结果（fast TX，cap500，rate5 < bulk10，6 s × 3 轮交替）

| 臂 | TTFT p50（三轮） | 中位 | 送达 | depth@到达 p50 | ai_jump | 驱逐 | AI 被拒 |
|---|---|---:|---:|---:|---:|---:|---:|
| fifo | 2005 / 2036 / 1989 ms | **2005 ms** | 38–41/60 | 500 | 0 | 0 | 214–296 |
| quota | 1916 / 1918 / 1926 ms | **1918 ms** | 40–41/60 | 500 | 0 | 156–205 | ~0–4 |
| ai-first | 36.2 / 41.9 / 60.4 ms | **41.9 ms** | 59–60/60 | 500 | 61–69 | 0 | 68–168 |
| both | 25.8 / 21.5 / 29.3 ms | **27.0 ms** | 60/60 | 500 | 60–66 | 121–178 | ~0–4 |

### 15.3 结论（可定稿）

1. **条件被摁住**：四臂 depth@到达 p50 全部 = 500，说明"队列满"是构造出来的，不是运气。
2. **ai-first 是唯一大幅改善时延的手段**：2005 → 41.9 ms（约 48×）；both 27.0 ms（约 74×）。
3. **quota 单独几乎不改善时延**（2005→1918，4%），但它的作用体现在别处：`evictions` 156–205 次、AI 被拒接近 0——它保护的是**准入**，服务顺序仍是 FCFS，所以 AI 仍排在 500 帧之后（约 2 s）。
4. fifo/quota 送达只有 38–41/60，是 2 s 排队时间让尾部请求超出客户端 6 s 窗口，不是丢包。
5. 本轮每臂 3 次极差很小（fifo ±24 ms，ai-first ±12 ms），协变量已同轮记录，可用于解释残余波动。

### 15.4 可写入报告的一句话

> 在受控满队列（500 帧）下，AI-first 把首块时延从 2.0 s 降到 42 ms，组合模式降到 27 ms；配额单独把准入拒绝从 ~250 次降到 ~0，但不改变服务顺序，因此时延仍约 1.9 s。

限制：应用层队列，非 MAC 队列；bulk 上限受笔记本路径 ~52 Mbps 约束。
