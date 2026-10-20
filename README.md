# BPI-R4 无线参数实时下发与调度器实验

OpenWrt 6.6.73 · MT7996（mt7996e）· BPI-R4（MT7988A）

针对 2026-10-16 课题组会议任务（EDCA/MCS/A-MPDU 参数实时修改的系统性实测验证 + 私有调度器编译部署）的实验项目：**所有实验数据、报告、脚本与补丁的单一版本管理仓库。**

## 核心结论

| 主题 | 结论 |
|---|---|
| EDCA 实时修改 | **即时生效、免重载**：nl80211/debugfs 固件直写，下发端到端时延中位数约 463.5 μs（5G 打流态），100s 时序实验全程无断流、Retr 0 |
| MCS 实时修改 | **命令可实时下发但对 AP 下行不生效**：iw set bitrates 走 mac80211 TX rate mask，mt76/mt7996 AP 下行 minstrel_ht 不消费该掩码；锁速后 station 速率 360.3 Mbit/s 仍高于锁定档上限，吞吐不降反升。生效需 STA 模式或驱动补丁 |
| A-MPDU 实时修改 | **待办**：运行态无写入通道（聚合参数关联协商期确定），需补 debugfs/vendor 写接口 |
| mac80211 WDRR 私有调度器 | 修改→编译→烧录→运行验证链路已跑通；双 AC 并发验证证明 fq 层 per-AC 加权**架构性无效**（fq 为 per-flow 粒度、AC 级调度在 txq 层），.orig 基线无性能退化 |

## 报告索引（docx）

| 文件 | 内容 |
|---|---|
| `无线参数实时下发时序验证实验报告.docx` | **统一维护的合并版报告**：实验一 EDCA 时序验证 + 实验二 MCS 实时修改时序验证（含生效性判别与根因） |
| `EDCA实时下发时序验证实验报告.docx` | 合并前 v1（EDCA 单实验），已被上表取代 |
| `mac80211 WDRR 调度器部署验证报告.docx` | WDRR 补丁的修改→编译→烧录→验证闭环 + §6.4 加权架构结论 + §6.5 基线对照 |
| `BPI-R4 AP下行EDCA参数实时调节实验指导书.docx` | EDCA 双轨验证（debugfs 回读 + netlink 下发）操作指导 |
| `调度器部署任务交接文档.docx` | 调度器任务交接说明 |

## 目录结构

```
_build/                 调度器补丁与编译链路（001-wdrr.patch、apply_wdrr.py、build*/verify* 脚本）
_work_timeline/         实验一手数据与编排脚本（edca_*/mcs_* 的 txt/csv/json/png + run_*.py）
_work_edca_timeline_report/  合并版报告生成脚本（make_doc.py、outline.md、SOURCE_DOCX.docx）
_work_wdrr_report/      调度器报告生成脚本
_work_systematic/       系统性实测报告生成脚本
_work_handoff/          交接文档生成脚本
_work_wdrr_edit/        WDRR 报告修订脚本
*.sh / *.py             板端/电脑侧实验脚本
```

> `_sdk/`（OpenWrt SDK 约 208MB）、`render_out*/`（渲染 PNG）、`*.ko/*.ipk`（编译产物）不入库，可重建。

## 实验复现

- 环境：电脑无线网卡 STA 直连板端 5G AP（phy0.1-ap0，SSID BPI-R4-5G），iperf3 反向打流（板端 server :5201，电脑 `-R -i 1`），电脑侧 iperf3 需 **3.2+**（3.1.3 不支持 `--forceflush`）。
- EDCA：`python run_edca_timeline.py --issue-sec 50 --duration 100 --out-prefix edca_tl_final`（板端 `python3 /root/edca_set.py phy0.1-ap0 0 1 3 7 0`）
- MCS：`python run_mcs_timeline.py --station <MAC> --issue-sec 50 --duration 100 --out-prefix mcs_tl`（板端 `iw dev phy0.1-ap0 set bitrates ...`）
- 数据口径：`*_events.json` 记录实测下发窗口，`*_iperf3.txt` 为每秒吞吐点；时钟以 iperf3 首条每秒行区间结束时刻对齐。

## 维护约定

- **只维护一份实验报告**：新增实验（如 A-MPDU）完成后并入 `无线参数实时下发时序验证实验报告.docx`，生成脚本在 `_work_edca_timeline_report/make_doc.py`。
- 报告数据必须可溯源：每次提交数据改动时同步更新对应 `*_events.json` / 数据文件。
