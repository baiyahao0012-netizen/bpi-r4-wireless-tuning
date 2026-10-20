# 《无线参数实时下发系统性实测报告》内容规划

## 任务
用户要求系统性实测 EDCA / A-MPDU / MCS 三类参数"命令下发"的实时程度——是否即时生效、是否需要重载 WiFi；明确 OpenWrt 软件队列、固件及硬件三者能支持的最小调度粒度。载体环境 BPI-R4（mt7996e 补丁驱动），方案 A：板子 5G 做 AP（BPI-R4-5G），电脑直连反向打流，板端命令走 SSH/串口。

## 写作类型
专业领域文书（工程技术测量报告），阿拉伯小数层级编号（1 / 1.1 / 1.1.1）。无模板创建，动态 TOC（正文 >5 页），真实 Heading 1/2 样式。

## 章节结构
1 概述
  1.1 任务背景（用户诉求：三类参数实时程度 + 最小调度粒度）
  1.2 测试目标
  1.3 结论摘要
2 测试环境与链路
  2.1 硬件与系统（BPI-R4；OpenWrt 24.10.0 r28427；内核 6.6.73；mt7996e 补丁驱动）
  2.2 无线拓扑（方案 A：phy0.1=5G AP ch149 HE80；phy0.0=2.4G AP；电脑 WLAN3 station 90:de:80:1c:6a:7a @192.168.1.126）
  2.3 工具（edca_set.py / measure_edca.py / iw 6.9 / iperf3 板端 server 5201）
3 实验设计
  3.1 三类参数调节入口侦察结果表
  3.2 实验矩阵（EDCA 已完成→补基线；MCS 主实验；A-MPDU 判定限制；txq 补充）
4 EDCA 实时下发实测
  4.1 下发通路（nl80211 SET_WIPHY+TXQ_PARAMS → mac80211 conf_tx → mt76 → 固件 MCU）
  4.2 生效即时性（120s 打流 + 60s 处激进档写入；瞬间 36.5→167 Mbps 下坠后恢复；无重连/无 AP 重启；398Mbps/25 重传）
  4.3 下发时延定量（5G 打流态 median 463.5μs；基线 AC=-1 median 91.7μs；专属 371.8μs；分布 min249/max1334/p90 627/p99 1297）
  4.4 与 2.4G 对比（基线 94.4 vs 91.7；打流态 322.1 vs 463.5）
5 MCS 速率掩码实时调整实测
  5.1 入口与命令形式（iw dev set bitrates；发现 station get/dump 必须写全 dev 形式，省略 dev 直接 usage；vht/he 单独掩码不生效，全层锁生效）
  5.2 实时生效证据（station tx bitrate 960.7 HE-MCS9 NSS2 → 360.3 HE-MCS7 NSS1 → 864.8 HE-MCS8 NSS2）
  5.3 吞吐三段式（基线 ~400 → 锁定段 24-37s 稳定 272 Mbps（-32%）→ 恢复 424；全程 1 重传无断流）
  5.4 收敛时间分析（命令瞬时下发；minstrel_ht 速率控制重收敛约 10s；区分"下发时延"与"算法收敛"）
6 A-MPDU 聚合参数：限制结论
  6.1 入口缺失证据（iw station set 仅 txpwr/airtime_weight/vlan；station debugfs 无 ampdu_factor/ampdu_density；mt76 debugfs 无 ampdu 节点）
  6.2 结论（聚合参数属关联期能力协商，运行时修改需断开重连或 wifi reload；非实时下发参数）
  6.3 观察点（agg_status / tx_stats / hw-queues）
7 软件队列调度实测
  7.1 队列结构（mac80211 4096 flow 队列；packet limit 8192；memory 16MB；mt76 xmit-queues DRR）
  7.2 实时调整验证（iw phy0 set txq quantum 300→512→65535 回读精确命中，免 reload）
  7.3 hw-queues 观察（PLE/PSE 固件硬件队列快照）
8 三层调度粒度分析
  8.1 软件队列层（mac80211 包粒度；DRR quantum 字节粒度 1~2^32）
  8.2 固件层（MT7996 MCU 命令：EDCA 专属 371.8μs；速率表更新瞬时；PLE/PSE 帧描述符队列）
  8.3 硬件层（基带发送引擎，下一帧即用新参数，μs 级）
  8.4 最小调度粒度结论表
9 结论矩阵（三类参数 × 即时生效/需否 reload/实测时延/粒度定位）
10 复现步骤（命令清单）
11 局限与后续

## 关键数据（全部来自本次实测，可溯源）
- EDCA 5G 打流态：median 463.5 / min 249.0 / max 1333.9 / mean 491.4 / p90 627.1 / p99 1296.8 μs（measure_edca.py phy0.1-ap0 0 1 3 7 0 100）
- EDCA 5G 基线（AC=-1）：median 91.7 / min 88.7 / max 148.2 / mean 93.1 / p90 96.2 / p99 115.9 μs
- 专属耗时 = 463.5 − 91.7 = 371.8 μs
- EDCA 120s 切换：全程 398 Mbps、25 重传；59-61s 区间 36.5→167 Mbps；前后段均值差异 <2%
- MCS：锁定前 960.7（HE-MCS9 NSS2）→ 锁定 360.3（HE-MCS7 NSS1）→ 恢复 864.8（HE-MCS8 NSS2）MBit/s
- MCS 吞吐三段式：基线 ~400 Mbps → 锁定段（24-37s）272 Mbps 稳定平台 → 恢复 424 Mbps；40s 全程 352 Mbps、1 重传
- txq：quantum 300 → 512 → 65535 bytes 实时生效；limit 8192 pkts、memory_limit 16MB、4096 队列
- 链路：5G 打流基线 60s=376 Mbps/7 重传；45s 佐证 315 Mbps/13 重传
- 2.4G 参考：基线 94.4、空闲 215.5、打流 322.1 μs

## 引用核查表
本报告全部数据来自本次实测（板端命令输出 + PC 端 iperf3 日志），不引用法规/标准/外部文献，无需联网核查。

## 格式要求
- A4、2.5cm 边距；Title 黑体 16pt 居中；Heading1 黑体 16pt 加粗黑色、Heading2 黑体 14pt、Heading3 黑体 12pt（真实 Heading 样式）
- 正文宋体 12pt、1.5 倍行距、首行缩进 2 字符、两端对齐
- 表格：表头浅灰 D9D9D9、表内 10.5pt、cantSplit、tblHeader、垂直居中、首列居中、数字右对齐
- 代码：Consolas 9pt
- 动态 TOC（Heading 1-2），目录后正文另起页
- 无 emoji；数字与单位一致（μs / Mbps / MBit/s）
