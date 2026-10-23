# A+ 每 STA 配额调度：实现与 2:1 / 4:1 验证

日期：2026-10-23

## 1. 目标

在现有 mac80211/mt76 链路上实现 per-STA 可配置配额，使 VIP STA 与普通 STA 的吞吐比可设为 2:1 或 4:1，同时保留 `ieee80211_next_txq()` / `ieee80211_return_txq()` 生命周期。

## 2. 实现 A：mt76 per-WCID 帧 token bucket

- `struct mt76_wcid` 增加 `tx_weight / tx_tokens / tx_token_jiffies`；
- `mt76_txq_schedule_list()` 在 `ieee80211_next_txq()` 后检查 token；不足则 `ieee80211_return_txq()` 并跳过；
- 每 10 ms 按 `weight × QUANTUM` 补 token，发送后按帧数扣减；
- debugfs `/sys/kernel/debug/ieee80211/phy0/mt76/sta_weight`：读 `MAC weight tokens`，写 `MAC weight`。

### 编译产物

| 模块 | 大小 | md5 |
|---|---|---|
| mt76.ko | 1,172,592 | `bc05b23788a77d45e3d445b5a470d9e3` |
| mt76-connac-lib.ko | 589,080 | `0ad1ea7663f914f4add67469c7f9e3e4` |
| mt7996e.ko | 1,362,744 | `e7584a121bf63f4195598b4efa325d78` |

### token bucket 实测

| 配置 | VIP | 普通 | 比值 | 问题 |
|---|---|---|---|---|
| QUANTUM=512，4:1 | 199 | 137 | 1.45:1 | token 补充太快，几乎不限制 |
| QUANTUM=32，4:1 | 21.1 | 6.08 | 3.47:1 | 比值接近，但总吞吐崩到 27 Mbit/s |
| QUANTUM=32，8:2 | 25.0 | 14.7 | 1.70:1 | 提高权重后总吞吐仍只有 40 Mbit/s |

结论：帧 token 在 txq 层门控会与 TCP/聚合互相拖累，能改变比值但无法同时保证绝对吞吐；需要改为**字节信用 + 更平滑的补充**，当前不作为交付方案。

## 3. 实现 B：per-STA 软件配额（nft policer）

在板端 `output` 链对普通 STA 的 IP 目的地址做限速，超出部分丢弃；VIP 不限速。TCP 会自动退避到限速值，VIP 获得剩余空口。

```sh
nft delete table ip vipq 2>/dev/null
nft add table ip vipq
nft add chain ip vipq out '{ type filter hook output priority 0; }'
nft add rule ip vipq out ip daddr <普通STA_IP> limit rate 9 mbytes/second accept
nft add rule ip vipq out ip daddr <普通STA_IP> drop
```

### 实测（3 轮，10 s 双流）

| 目标 | 普通限速 | VIP 平均 | 普通平均 | 实测比值 |
|---|---|---|---|---|
| 2:1 | 12 MB/s（96 Mbit/s） | 231.7 | 108.7 | **2.13:1** |
| 4:1 | 9 MB/s（72 Mbit/s） | 300.7 | 81.5 | **3.69:1** |
| 4:1 参考 | 6 MB/s（48 Mbit/s） | 330.7 | 54.6 | 6.06:1 |

说明：VIP 绝对值反而高于无配额基线（约 174 Mbit/s），因为普通被限速后空口竞争下降；代价是普通被压到设定值。

## 4. 配置脚本

`vip_ratio.sh`：

```sh
vip_ratio.sh 2 <普通STA_IP>   # 2:1，12 MB/s
vip_ratio.sh 4 <普通STA_IP>   # 4:1，9 MB/s
vip_ratio.sh off              # 关闭
```

仅对板端本地生成流量（iperf3 server）有效；WAN→STA 转发流量需再加 `forward`/`postrouting` 链。

## 5. 原始数据

- `_work_final/aplus_policer_results.csv`：2:1（12 MB/s）与 4:1（6 MB/s）各 3 轮；
- `_work_final/aplus_policer_4to1_9.csv`：4:1（9 MB/s）3 轮；
- `_work_final/run_aplus_policer.py`：测试编排；
- `_build/apply_aplus.py` / `build_aplus.sh`：A+ token 实现与编译。

## 6. 结论

1. A+ token bucket 控制面（`sta_weight` 读写）已跑通，但帧 token 方案吞吐不稳定，不作为最终交付；
2. per-STA nft 配额可稳定做到 **2:1（2.13）** 与 **4:1（3.69）**，VIP 绝对值 230–300 Mbit/s；
3. 该配额是“限普通、保 VIP”，不是严格加权公平；若要精确 2.00/4.00，需要闭环校准或字节信用调度；
4. 生产环境若需 WAN→STA 也生效，需把规则挂到 `forward`/`postrouting` 并启用 bridge netfilter。
