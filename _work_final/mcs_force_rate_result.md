# MCS 锁定调查结果（2026-10-23）

## 结论

- 标准 `iw dev ... set bitrates he-mcs-5 ...` 对 AP 下行**不生效**：station tx 仍在 HE-MCS10/MCS7，吞吐不变；
- mt7996 固件自带 **per-STA fixed_rate**（`UNI_RA_FIXED_RATE`）在本板未编译出 debugfs；补了 phy 级 `force_rate` 调 `mt7996_mcu_set_fixed_rate_ctrl()`，固件 ACK 但 station tx/吞吐不变，说明该接口不是 AP 下行 tx rate 的生效路径；
- **驱动 txwi 的 `MT_TXD1_FIXED_RATE` 路径有效**：把 5G basic rate table 35 写成 legacy 6M，并对数据帧强制 `MT_TXD1_FIXED_RATE` 后，station tx 立刻变为 **6.0 Mbit/s**；
- 但把 table 35 写成 HE-MCS0（`0x600`）仍显示 6.0 Mbit/s，说明 **table 35 是 legacy basic 表**，不接受 HE 编码；HE MCS 锁定需要**自定义 table index + 正确 HE rate 编码**，并在 txwi 指向该 index；
- 代价：固定 rate 会置 `MT_TXD3_BA_DISABLE`，关闭聚合，吞吐降到单 MCS 水平。

## 关键证据

| 操作 | station tx | 吞吐 |
|---|---|---|
| 基线 | HE-MCS10 1080.6 Mbit/s | 约 420 Mbit/s |
| `iw set bitrates he-mcs-5 2:0` | HE-MCS7 720.6 | 约 403 Mbit/s |
| `iw set bitrates vht-mcs-5 2:0` | VHT-MCS4 351 | 约 190 Mbit/s |
| `force_rate` 调 firmware RA fixed | 不变 | 不变 |
| `force_rate` 置 table 35=6M + txwi FIXED_RATE | **6.0 Mbit/s** | 未测到（iperf 连接超时） |

## 后续可行路径

1. 选一个空闲 table index（如 30），调用 `mt7996_mcu_set_fixed_rate_table()` 写 HE-MCS0 编码；
2. 在 `mt7996_mac_write_txwi()` 的 fixed-rate 分支把 `MT_TXD6_TX_RATE` 指向该 index；
3. 用 `MT_TXD1_FIXED_RATE` 强制所有数据帧；
4. 验证 station tx 变为 HE-MCS0（80MHz NSS2 约 17 Mbit/s），再逐步提高 MCS。

## 代码

- `_build/apply_force_rate.py`（firmware RA fixed，验证无效）
- `_build/apply_txwi_rate.py`（txwi fixed rate，验证有效）
- `_build/build_txwi_rate.sh`

## 注意

当前板端已重启，`force_rate` 默认关闭；table 35 由初始化恢复为 basic rate，不影响正常使用。
