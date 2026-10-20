# BPI-R4 mac80211 WDRR 调度器部署验证报告 — 内容大纲

## 交付物
- 文件名：mac80211 WDRR 调度器部署验证报告.docx
- 载体：Word（本地新建，无模板）
- 体裁：专业领域文书（工程技术部署验证报告）
- 篇幅：约 6–9 页，含动态目录（正文超过 5 页且具导航价值，按写作分类规则必须使用 TOC）
- 编号体系：阿拉伯小数层级（1 → 1.1 → 1.1.1）
- 风格：严谨、结果导向、定量可复核；中文正文；不使用 emoji

## 章节规划
1. 任务概述
   - 目标：为 mac80211 的 fq(DRR) 队列调度器增加 per-AC 加权（WDRR）能力
   - 背景：OpenWrt 24.10.0 / 内核 6.6.73 / BPI-R4（MT7988A + MT7996 三频）
   - 验收口径：修改→编译→烧录→运行验证全链路打通，含打流回归

2. 补丁方案
   - 2.1 修改点：include/net/fq.h（flow 增加 quantum 字段）、fq_impl.h（出队 deficit 逻辑）、net/mac80211/tx.c（fq_weight 模块参数 + WDRR 打印）
   - 2.2 模块参数 fq_weight[IEEE80211_NUM_ACS]：默认 1,1,1,1，sysfs 可写，无需重编译即可调整各 AC 权重
   - 2.3 修改方式：Python 单行锚点替换脚本（apply_wdrr.py，5 处替换），弃用标准 unified diff（空行 malformed）

3. 编译产物
   - 3.1 编译链：WSL 环境，OpenWrt SDK（mediatek_filogic gcc-13.3.0 musl），build10.sh：clean→prepare→双树 apply→verify→compile -j24→nm/strings 校验
   - 3.2 产物校验：mac80211.ko 6603848 B，md5 49f2aca91f3228adcd83b205f5338d61（Windows 与板端一致）；板端使用 regular variant

4. 部署过程
   - 4.1 管理通道演进：5G AP 直连不稳定 → STA 连热点（隐藏 SSID，scan_ssid=1）→ 最终 2.4G AP（BPI-R4）+ USB 网卡上网的双网卡分工
   - 4.2 防火墙处理：wwan 属 wan zone（input=REJECT）→ 增加 Allow-SSH-WWAN 放行规则（src=wan, dest_port=22, proto=tcp, target=ACCEPT）
   - 4.3 文件传输与烧录：scp -O（legacy 协议，板端无 sftp-server）→ 备份 .orig → 覆盖 → md5 校验 → sync → reboot

5. 运行验证（烧录后）
   - 5.1 模块参数：cat /sys/module/mac80211/parameters/fq_weight → 1,1,1,1（默认值命中）
   - 5.2 内核日志：dmesg 输出 "mac80211: private WDRR scheduler active (fq_weight=1,1,1,1)"（时间戳 35.125138）
   - 5.3 运行时改参：echo 2,1,1,1 > fq_weight → 回读 2,1,1,1（sysfs 可写，运行时生效）
   - 5.4 内核版本：6.6.73

6. 打流回归
   - 6.1 2.4G 链路（iperf3 反向 30s）：10.2 Mbits/sec（sender）/ 10.1（receiver），Retr 11，无崩溃
   - 6.2 5G 链路（iperf3 反向 30s）：53.6 Mbits/sec（sender）/ 53.4（receiver），Retr 0，无崩溃、无跌落
   - 6.3 结果解读：本回归验证调度器在真实流量下的稳定性（功能口径）；53.6 Mbps 为默认 MCS/单流水平，与原报告 5G 高吞吐（EDCA/MCS 专项调优，960.7/360.3/864.8 MBit/s 三段式）量级不同，不可直接对比；链路质量差异（邻居 AP 干扰）也属影响因素

7. 环境与配置快照
   - 7.1 硬件与系统：BPI-R4、OpenWrt 24.10.0 r28427-6df0e3d02a、内核 6.6.73
   - 7.2 无线拓扑：2.4G AP（BPI-R4，ch6 HE20）+ 5G AP（BPI-R4-5G，ch149 HE80）已恢复；sta0 已禁用；radio1 恢复 AP 模式
   - 7.3 驱动文件：/lib/modules/6.6.73/mac80211.ko（WDRR 版，md5 49f2aca91f3228adcd83b205f5338d61）；备份 /lib/modules/6.6.73/mac80211.ko.orig；/tmp/mac80211.ko（上传副本）
   - 7.4 服务状态：dropbear 22、uhttpd 80/443、dnsmasq 53、iperf3 5201（daemon）

8. 回滚与注意事项
   - 8.1 回滚：cp .orig 覆盖 + sync + reboot
   - 8.2 注意事项：iperf3 server 重启后需手动拉起（iperf3 -s -p 5201 -D）；scp 必须用 -O；wifi reload 会闪断当前无线链路；Windows 热点对空闲 STA 有 inactivity 踢出行为

## 引用核查表
| 引用名称 | 标准编号/文号 | 发布机关 | 发布/修订年份 | 现行有效性 | 核实状态 | 搜索来源URL |
|---|---|---|---|---|---|---|
| （本报告为工程实测记录，全部数据来自本次任务实际验证输出，无外部法规/标准引用） | — | — | — | — | 不适用 | — |

## 关键事实登记（写入正文前逐一核对）
- 板子型号/系统：BPI-R4，OpenWrt 24.10.0 r28427-6df0e3d02a，内核 6.6.73
- 驱动产物：/lib/modules/6.6.73/mac80211.ko，6603848 B，md5 49f2aca91f3228adcd83b205f5338d61
- fq_weight 默认 1,1,1,1；运行时 echo 2,1,1,1 回读命中
- dmesg 标记：[35.125138] mac80211: private WDRR scheduler active (fq_weight=1,1,1,1)
- 2.4G 打流：10.2/10.1 Mbits/sec，30 s，Retr 11
- 5G 打流：53.6/53.4 Mbits/sec，30 s，Retr 0
- 防火墙规则：Allow-SSH-WWAN（src=wan, dest_port=22, proto=tcp, target=ACCEPT）
- 原报告数据（仅引用说明量级差异，不展开）：5G MCS 三段式 960.7→360.3→864.8 MBit/s、EDCA 463.5μs

## 验收要点
- 全部数据来自本次实测输出（工具结果），无编造
- 表格数据列右对齐、文本左对齐、表头浅灰（#D9D9D9）、行不跨页（cantSplit）、表头跨页重复（tblHeader）
- Heading 使用真实样式，标题黑色、不加句号
- 正文宋体 12 pt、1.5 倍行距、首行缩进 2 字符；标题黑体；西文 Times New Roman
- 动态 Word TOC（基于 Heading 1–2），封面/目录/正文分页，页码正文起
