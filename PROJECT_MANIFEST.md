# BPI-R4 无线项目总索引（交付版）

> 仓库：<https://github.com/baiyahao0012-netizen/bpi-r4-wireless-tuning>（private）
> 分支：`main` · 交付标签：`project-handoff-20261025`
> 环境：BPI-R4 2.5GE PoE / OpenWrt 24.10.0 / Linux 6.6.73 / MT7996（BPI-R4-NIC-BE14）

## 1. 项目范围

本项目包含两条主线：

1. **无线参数实时性系统实测**：EDCA、A-MPDU 聚合窗口、MCS 速率的下发时延、生效性、是否需重载 WiFi、最小调度粒度；
2. **私有调度器与 VIP 方案**：mac80211 fq/WDRR 补丁、mt76 per-STA token bucket（A+）、per-STA 软件配额、VIP 四组对比实验。

## 2. 核心结论（速览）

| 主题 | 结论 |
|---|---|
| EDCA | **免重载、即时生效**；命令→固件 ACK p50 220–342 μs；VO/BK 比例 0.1–0.3 s 内翻转 |
| A-MPDU | **免重载**；`agg_win_cap=2` 写入 10.5–11.5 ms，下行 402→74.3 Mbit/s，业务 0.5–3 s 进入稳态 |
| MCS | 标准 `iw set bitrates` 对 AP 下行**不生效**；固件 RA fixed_rate 也无效；驱动 txwi `MT_TXD1_FIXED_RATE` + 固定 table **已实测锁到 6.0 Mbit/s**，HE-MCS0 需自定义 table index |
| WDRR | 修改→编译→烧录→加载→运行标记链路跑通；fq 层 per-AC 加权**架构性无效**；per-STA 未实现 |
| A+ token | per-WCID 帧 token 控制面可用，但数据面吞吐不稳定；不作为最终交付 |
| VIP 配额 | per-STA nft 配额：2:1 → 2.13:1（231.7/108.7），4:1 → 3.69:1（300.7/81.5） |
| VIP 四组 | 同频 AC 只在快 STA 上 2–3:1；2.4G 同型号强但普通饿死；跨频隔离最高 80:1 |

## 3. 目录索引

| 目录/文件 | 内容 |
|---|---|
| `_work_final/` | 汇总报告、CSV 原始数据、图表、VIP/A+ 结果、`modules/` 编译产物 |
| `_work_timeline/` | EDCA/MCS/A-MPDU 时序原始数据、逐秒 iperf3、编排脚本 |
| `_build/` | 补丁生成脚本、编译脚本、WDRR patch、A+/force_rate 实现 |
| `_work_edca_timeline_report/` | 合并版 docx 报告生成脚本 |
| `_work_wdrr_report/`、`_work_systematic/` | WDRR/系统性报告生成脚本 |
| `README.md` | 早期实验索引与复现说明（部分结论以本索引/最新报告为准） |
| `PROJECT_MANIFEST.md` | 本文件 |

### 关键文件

- `_work_final/FINAL_SUMMARY_FOR_REPORT.md`：两项任务的完整文字总结；
- `_work_final/BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx`：合并版报告；
- `_work_final/quantitative_timing.md`：时延/粒度定量；
- `_work_final/aplus_results.md`、`vip_ratio.sh`：A+ 配额与 2:1/4:1；
- `_work_final/mcs_force_rate_result.md`：MCS 锁定调查；
- `_work_final/vip_four_groups_summary.md`：VIP 四组；
- `_work_final/modules/`：EDCA/A-MPDU/MCS/WDRR/A+ 模块与 `edca_set`。

## 4. 编译产物与 md5

| 模块 | 用途 | md5 |
|---|---|---|
| `mac80211.wdrr.ko` | WDRR fq 加权补丁 | `49f2aca91f3228adcd83b205f5338d61` |
| `mt7996e_edca_eeprom.ko` | EDCA debugfs + 强制默认 EEPROM | `bb9f774c3fcf5aa44c675cad8f9ddf4c` |
| `mt7996e_ampdu_eeprom.ko` | A-MPDU `agg_win_cap` | `226812a1edc1159026d3305273b1c496` |
| `mt76.mcs.ko` | MCS force_mcs 实验 | `98950b1412ffb9c5fc110c04022462ed` |
| `mt76-connac-lib.mcs.ko` | 同上 | `750d1abde6decb9afdbdcf439820548e` |
| `mt7996e.mcs.ko` | 同上 | `0ac042a8fbfe4b39ba08c4f2999132be` |
| `aplus/mt76.ko` | A+ per-WCID token | `bc05b23788a77d45e3d445b5a470d9e3` |
| `aplus/mt76-connac-lib.ko` | A+ | `0ad1ea7663f914f4add67469c7f9e3e4` |
| `aplus/mt7996e.ko` | A+ + `force_rate` debugfs | `e3915b8cfc57bdca5e4a7e1ba2676a79` |

> 注意：A+ 模块与主线 mt76 有 ABI 差异，必须三件套一起替换；替换前备份 `/lib/modules/6.6.73/*.ko`。

## 5. 复现入口

### EDCA

```sh
# 板端
/root/edca_set phy0.1-ap0 0 1 3 7 0
cat /sys/kernel/debug/ieee80211/phy0/mt76/edca
```

### A-MPDU

```sh
echo 2 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap
# 打流后写回 0
```

### MCS（已验证的 txwi 固定速率）

```sh
echo he0 > /sys/kernel/debug/ieee80211/phy0/mt76/force_rate
# 当前实现 table 35=6M，station tx 会锁到 6.0 Mbit/s；HE MCS0 需自定义 table
```

### VIP 2:1 / 4:1

```sh
vip_ratio.sh 2 <普通STA_IP>   # 12 MB/s
vip_ratio.sh 4 <普通STA_IP>   # 9 MB/s
vip_ratio.sh off
```

### A+ token 调试

```sh
cat /sys/kernel/debug/ieee80211/phy0/mt76/sta_weight
echo "<VIP_MAC> 4" > /sys/kernel/debug/ieee80211/phy0/mt76/sta_weight
echo "<NORMAL_MAC> 1" > /sys/kernel/debug/ieee80211/phy0/mt76/sta_weight
```

## 6. 构建

- EDCA/A-MPDU/MCS：`_build/build_v4_clean.sh` / `_build/build_v3.sh` 等；
- WDRR：`_build/apply_wdrr.py` + 对应 build；
- A+ token：`_build/build_aplus.sh`；
- A+ + force_rate：`_build/build_txwi_rate.sh`；
- 编译依赖 OpenWrt SDK 24.10（`_sdk/` 不入库，按 README 下载）。

## 7. 数据口径与限制

- EDCA 时延为 `sendto(nl80211)→内核 ACK`，不是空口生效时延；
- A-MPDU write 时延与业务收敛时间分开；
- MCS 负结果是固件 RC 行为，不是实验失败；txwi 固定速率会关闭 BA/聚合；
- 板端 MT7996 EEPROM 读取异常，使用强制默认 EEPROM 诊断构建，绝对吞吐与完全原厂校准有差异；
- 两个 USB 网卡同时高负载会互相影响，跨频测试需错开启动/限速；
- `_work_recover/`、`_sdk/`、个人文件不入库。

## 8. OAF AI 应用加速（2026-10-25）

- OAF 侧已完成豆包/千问/元宝的服务识别验证（AppID 1900/1901/1902；TCP 443 + 域名，3 正/1 静置/1 对照）。
- OAF v7.0.1 将 AppID 写入 conntrack mark 低 16 位；加速层用 nft 匹配 `ct mark & 0xffff == 1900`，打 DSCP EF，进入 mac80211 AC_VO。
- 工具：`_work_final/oaf_accel/oaf_accel.sh`（install/remove/status/verify）、`oaf_ab_capture.sh`（A/B 抓包与 app 表采样）、`README.md`（原理/限制/步骤）。
- 注意：当前 OAF 规则只覆盖 `doubao.com` TCP 443；图片/语音/QUIC 可能不在内；OAF 验证环境为 OpenWrt 25.12.5/6.12.94，勿与 24.10/6.6.73 的 A+ 模块混用。

## 9. 维护约定

- 新实验完成后更新本索引 + `_work_final/FINAL_SUMMARY_FOR_REPORT.md`；
- 驱动模块必须记录 md5；
- 原始 CSV/时序数据与报告同提交；
- 大文件（`*.ko`、`*.ipk`）按需 `git add -f`，不要提交 `_sdk/`、`_work_recover/`、个人文档。
