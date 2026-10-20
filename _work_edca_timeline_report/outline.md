# 无线参数实时下发时序验证实验报告 · 内容规划（EDCA + MCS 合并版）

## 报告目标与读者
- 目标：按 2026-10-16 会议任务 1 定义，将 EDCA 时序验证实验与 MCS 实时修改实验合并为一份统一实验报告，用户只维护此一份。
- 读者：课题组（田鸿雅/白亚豪/李云泽/肖阳）与评审（高雅玙）。
- 文种：工程技术实验验证报告（专业领域文书），阿拉伯小数层级编号。

## 结构（章节、事实依据、重点）
1. 实验背景与目的
   - 会议任务原文：完成 EDCA 实时修改的时序验证实验（同时统计与下发、记录下发时刻），尽快完成聚合（AMPDU）、MCS 等参数的实时修改实验 @白亚豪。
   - 评审追问（高雅玙）："立即"是定性说法，能否定量测量，毫秒级还是微秒级。
   - 本报告涵盖 EDCA 时序验证（实验一）与 MCS 实时修改（实验二）两个实验，A-MPDU 仍待办。
2. 实验环境与链路
   - BPI-R4（MT7988A + MT7996，mt7996e 补丁驱动），OpenWrt 内核 6.6.73；5G AP 下行 phy0.1-ap0（BPI-R4-5G，ch149 HE80，WPA2-PSK）。
   - 电脑无线网卡 STA 直连（实验二记录 station MAC c0:35:32:19:cc:fb，信号 -39 dBm，下行协商 HE-MCS8/2流 ≈ 864.8 Mbit/s）。
   - 工具：EDCA——板端 edca_set.py（nl80211 下发）+ debugfs 回读；MCS——iw set bitrates（NL80211 TX rate mask）+ station dump 回读；iperf3 反向打流（板端 server :5201 + 电脑 -R -i 1）。
   - 时钟对齐：iperf3 首条每秒行区间结束时刻（≈1.00s）对齐 perf_counter 原点。
3. 实验一：EDCA 实时下发时序验证
   - 3.1 方法：100s 打流每秒 1 点，t=50s 下发 BE 激进档（edca_set.py phy0.1-ap0 0 1 3 7 0：aifs=1/cwmin=3/cwmax=7/txop=0），默认档 BE 3/15/63/63；实测下发窗口 50.000~50.418s；前后 debugfs 回读。
   - 3.2 下发链路验证：netlink 返回成功（family id=27）、debugfs 回读命中（cwmin fls4→2、cwmax fls6→3）、100s 无断流、Retr 0、免重载。
   - 3.3 时序图（图1，edca_tl_final.png）：t=50.418s 竖线，下发前后无跳变。
   - 3.4 统计对比（表1）：前段 mean 50.0/median 50.5；后段 mean 51.6/median 51.8；Δ+1.62（+3.2%）噪声内。
4. 实验二：MCS 实时修改时序验证
   - 4.1 方法：同口径——100s 打流每秒 1 点，t=50s 下发锁速命令（iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0，全层最低档），实测下发窗口 50.005~50.253s；打流中 station dump 回读速率；结束后恢复自动速率（set bitrates 无参数）。
   - 4.2 下发链路验证：命令实时下发成功（rc=0）、免重载、毫秒级窗口。
   - 4.3 时序图（图2，mcs_tl.png）：t=50.3s 竖线，吞吐无跳变（pre_mean 49.1、无拐点、min 32.2/max 58.9）。
   - 4.4 生效性判别：决定性实验——仅锁 legacy-5 6（802.11a 6Mbps）后打流 30s，吞吐仍 46.1~59.8 Mbit/s 无跳变；station tx bitrate 锁速前后打流中均为 360.3 Mbit/s，未随掩码变化。
   - 4.5 结论与根因：命令可实时下发但对 AP 下行速率无约束——mt76/mt7996 AP 下行速率控制（minstrel_ht）不消费 cfg80211 TX rate mask；对比 EDCA 走 debugfs 直写固件参数故实时生效。旧系统性实测报告"MCS 三段式 960.7/360.3/864.8"系 station dump 瞬时速率波动，锁速未生效。
   - 4.6 局限：未做 2.4G AP 对照与 STA 模式验证（板端已无 STA 接口，需重搭链路）。
5. 总结与会议任务闭环状态
   - 表2 EDCA/MCS 对比：命令通道、下发窗口、免重载、是否生效、生效通道、吞吐影响。
   - 任务1 状态：EDCA 时序验证完成（同时统计与下发、记录下发时刻、时序图）；MCS 实时修改实验完成（结论：AP 模式不生效，生效需 STA 模式或驱动补丁）；A-MPDU 实时修改待办（无写入通道）。
   - 遗留事项回答：哪些命令即时生效（EDCA 生效、MCS mask 不生效）；软件队列最小调度粒度见 WDRR 报告（fq flow 级，AC 级在 txq 层）。
6. 数据与复现
   - 实验一：edca_tl_final_iperf3.txt / edca_tl_final_events.json / edca_tl_final.csv；复现 run_edca_timeline.py --issue-sec 50 --duration 100 --out-prefix edca_tl_final。
   - 实验二：mcs_tl_iperf3.txt / mcs_tl_events.json / mcs_tl.csv；复现 run_mcs_timeline.py --station c0:35:32:19:cc:fb --issue-sec 50 --duration 100 --out-prefix mcs_tl。
   - 电脑侧 iperf3 需 3.2+（3.1.3 不支持 --forceflush）；实验后 EDCA 已恢复默认档、MCS 掩码已清除。

## 引用核查表
| 引用名称 | 出处 | 核实状态 | 来源 |
|---|---|---|---|
| 会议任务定义（时序验证 + MCS/AMPDU @白亚豪） | 2026-10-16 飞书会议纪要《下一步工作计划·硬件平台方向》 | 已核实（本会话读取） | https://hustdian.feishu.cn/docx/FkNDd6tjYohofBxmHrFcWeMHn7e |
| 评审评论（高雅玙：定量测量毫秒/微秒级） | 同上纪要评论 c1 | 已核实 | 同上 |
| EDCA 下发时延 median 463.5μs（5G 打流态） | 《无线参数实时下发系统性实测报告》 | 已核实（本会话读取） | D:\Desktop\kaggle\EDCA恢复材料\无线参数实时下发系统性实测报告.docx |
| 实验一全部数据 | 本会话实测 | 一手数据 | _work_timeline/edca_tl_final_*.txt/json/csv |
| 实验二全部数据 | 本会话实测 | 一手数据 | _work_timeline/mcs_tl_*.txt/json/csv |

## 格式
- A4、2.5cm 边距；Title 黑体 18pt；Heading1 黑体 16pt、Heading2 黑体 14pt；Normal 宋体 12pt 1.5 倍行距首行缩进 2 字符；Caption 宋体 10.5pt（图下）；Table Text 宋体 10.5pt。
- 阿拉伯小数层级；标题黑色无下划线；页脚居中页码。
- 预计约 3000 字 + 2 图 + 2 表，约 5 页，不建目录（未达 5000 字阈值）。
- 图1=EDCA 时序图、图2=MCS 时序图；表1=EDCA 统计对比、表2=EDCA/MCS 对比。
- 全部数据来自实测，不编造；无表情、无口语化。
