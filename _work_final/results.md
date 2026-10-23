# BPI-R4 EDCA / A-MPDU / MCS 实时性实测 + WDRR 部署验证（2026-10-22）

环境：OpenWrt 24.10.0 r28427，内核 6.6.73，MT7996（BPI-R4-NIC-BE14）。
拓扑：板端 5G AP `phy0.1-ap0`（ch149 HE80）← PC USB WiFi（192.168.240.126）；板端 2.4G STA `phy0.0-sta0` 连手机热点 Bai（192.168.140.209），为 PC 提供外网；PC 有线 192.168.240.2 ↔ 板端 192.168.240.1。

## 结论

| 主题 | 结论 | 关键数据 |
|---|---|---|
| EDCA 下行实时修改 | **即时生效，无需重载 WiFi** | 下发→ACK p50 220.3 μs（空载）/ 300.7 μs（打流）；hostapd PID 不变；STA connected time 连续；20 s 打流 0 Retr |
| A-MPDU 聚合窗口 | **即时生效，无需重载 WiFi** | cap=0：402 Mbit/s；cap=2：74.3 Mbit/s（−81.5%）；写回 0 立即恢复 |
| MCS 锁定 | **节点可写，AP 下行不生效** | force_mcs=0/1 时 station tx 仍 864.8/960.7 Mbit/s，吞吐 348/342 Mbit/s |
| 最小调度粒度 | 软件：包/帧；固件：MCU 命令；硬件：PPDU/A-MPDU | EDCA 命令 147–885 μs；聚合窗口以 MPDU 计 |
| WDRR 调度器 | **修改→编译→烧录→加载→运行标记全通** | mac80211 md5 49f2…；fq_weight 可读写；dmesg 出现 private WDRR scheduler active |

## EDCA

初始回读（hostapd 启动后）：

| ACI | aifs | cwmin | cwmax | txop | fls |
|---|---|---|---|---|---|
| 0 BE | 3 | 15 | 63 | 0 | 4/6 |
| 1 BK | 7 | 15 | 1023 | 0 | 4/10 |
| 2 VI | 1 | 7 | 15 | 94 | 3/4 |
| 3 VO | 1 | 3 | 7 | 47 | 2/3 |

`/root/edca_set phy0.1-ap0 0 3 7 15 0` 后回读 BE = 3/7/15/0，fls 3/4，无需重载。

时延：

| 场景 | n | min | p50 | p95 | max |
|---|---|---|---|---|---|
| 连续 50 次 | 50 | 147.2 | 220.3 | 381.5 | 884.6 μs |
| 20 s 打流中 15 次 | 15 | 235.8 | 300.7 | 550.5 | 689.0 μs |

20 s 下行 iperf3：371 Mbit/s，逐秒 343–397，Retr 0；hostapd PID 1919/1867 不变；connected time 61→76 s。

## A-MPDU

| 配置 | 吞吐 | Retr | 说明 |
|---|---|---|---|
| cap=0 | 381 Mbit/s | 2 | 基线 |
| cap=2 | 74.3 Mbit/s | 0 | ≤2 MPDU/A-MPDU |
| cap=0 恢复 | 402 Mbit/s | 0 | 立即恢复 |

dmesg：`agg_win_cap: cap=2 applied to 2 station(s)` / `cap=0 applied to 2 station(s)`。

## MCS

| force_mcs | station tx | 吞吐 | 结果 |
|---|---|---|---|
| 0 | 864.8 Mbit/s HE-MCS8 | 348 Mbit/s | 未锁到 MCS0 |
| 1 | 960.7 Mbit/s HE-MCS9 | 342 Mbit/s | 未锁到 MCS1 |
| 255 | 960–1080 Mbit/s | 371–402 Mbit/s | 自动 |

结论：mt7996 固件 RC 不消费主机 `rx_mcs_bitmask`，仅改该字段无法锁 AP 下行速率；需改固件 rate table 或走 STA 模式。

## WDRR

- 产物：mac80211.ko 6,603,848 B，md5 `49f2aca91f3228adcd83b205f5338d61`
- 已烧录 `/lib/modules/6.6.73/mac80211.ko`，原厂备份 `mac80211.ko.stock`（`d562…`）
- `fq_weight` 默认 1,1,1,1；写 4,1,1,1 回读成功
- dmesg：`mac80211: private WDRR scheduler active (fq_weight=1,1,1,1)`
- 架构结论（历史）：fq 为 per-flow，AC 调度在 txq 层，per-AC 权重互相抵消；BE:VO=4:1 时吞吐仍约 1:1

## 产物

- `_work_final/BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx`
- `_work_final/modules/`：EDCA / A-MPDU / MCS 三套 ko、`edca_set` 静态工具及源码、WDRR mac80211.ko

## 复现

```sh
/root/edca_set phy0.1-ap0 0 3 7 15 0
cat /sys/kernel/debug/ieee80211/phy0/mt76/edca

echo 2 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap
iperf3 -c 192.168.240.1 -B 192.168.240.126 -t 10 -R -i 2
echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap

echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/force_mcs
echo 255 > /sys/kernel/debug/ieee80211/phy0/mt76/force_mcs

cat /sys/module/mac80211/parameters/fq_weight
dmesg | grep WDRR
```
