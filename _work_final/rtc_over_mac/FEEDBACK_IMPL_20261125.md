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
