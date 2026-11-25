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
