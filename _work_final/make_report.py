# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUT = r"D:\Desktop\AI 辅助对话\_work_final\BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

doc = Document()
sec = doc.sections[0]
sec.top_margin = Cm(2.2); sec.bottom_margin = Cm(2.2)
sec.left_margin = Cm(2.4); sec.right_margin = Cm(2.4)

def cnfont(run, name="Microsoft YaHei", size=10.5, bold=None, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    if bold is not None: run.bold = bold
    if color: run.font.color.rgb = color
    r = run._element
    r.rPr.rFonts.set(qn('w:eastAsia'), name)
    r.rPr.rFonts.set(qn('w:ascii'), name)
    r.rPr.rFonts.set(qn('w:hAnsi'), name)

def para(text="", size=10.5, bold=False, align=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.25
    if align is not None: p.alignment = align
    r = p.add_run(text); cnfont(r, size=size, bold=bold)
    return p

def h(text, level=1):
    p = doc.add_heading(level=level)
    r = p.add_run(text)
    cnfont(r, size={1:16,2:13,3:11.5}.get(level,11), bold=True,
           color=RGBColor(0x1F,0x3B,0x57))
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    return p

def bullets(items, size=10.5):
    for it in items:
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(it); cnfont(r, size=size)

def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    hdr = t.rows[0].cells
    for i, x in enumerate(headers):
        hdr[i].text = ''
        p = hdr[i].paragraphs[0]
        r = p.add_run(x); cnfont(r, size=9.5, bold=True)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for row in rows:
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ''
            p = cells[i].paragraphs[0]
            r = p.add_run(str(x)); cnfont(r, size=9.5)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

def code(lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(line)
        r.font.name = 'Consolas'; r.font.size = Pt(8.5)
        r._element.rPr.rFonts.set(qn('w:eastAsia'), 'Consolas')
        r.font.color.rgb = RGBColor(0x33,0x33,0x33)

# ---------- 标题 ----------
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('BPI-R4 AP 下行 EDCA / A-MPDU / MCS 实时性实测\n与私有 WDRR 调度器部署验证报告')
cnfont(r, size=18, bold=True, color=RGBColor(0x14,0x2B,0x45))
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('OpenWrt 24.10.0 · 内核 6.6.73 · MT7996 · 2026-10-22')
cnfont(r, size=10, color=RGBColor(0x55,0x55,0x55))
doc.add_paragraph()

# ---------- 摘要 ----------
h('一、结论摘要', 1)
table(['主题','结论','关键数据'],
[
 ['EDCA 下行实时修改','即时生效，无需重载 WiFi','下发→回读 p50 220.3 μs；打流态 p50 300.7 μs；hostapd PID 不变、STA 不掉线、20 s 打流 0 Retr'],
 ['A-MPDU 聚合窗口','即时生效，无需重载 WiFi','cap=0：402 Mbit/s；cap=2：74.3 Mbit/s（−81.5%）；写回 0 立即恢复'],
 ['MCS 锁定','debugfs 节点可写，但 AP 下行不生效','force_mcs=0/1 时 station tx 仍为 HE-MCS8/9（864.8/960.7 Mbit/s），吞吐 348/342 Mbit/s，基本不变'],
 ['最小调度粒度','软件：包/帧；固件：MCU 命令；硬件：PPDU/A-MPDU','EDCA 命令端到端 147–885 μs；聚合窗口以 MPDU 为单位'],
 ['WDRR 调度器','修改→编译→烧录→加载→运行标记全部打通','mac80211 md5 49f2…；fq_weight 可读写；dmesg 出现 private WDRR scheduler active'],
],
 widths=[3.0,4.2,8.2])

para('一句话：EDCA 与 A-MPDU 都可以在 AP 运行中实时改、立即生效、不需要 wifi reload；MCS 的主机侧速率掩码仍然不被 mt7996 固件 RC 消费，属于“命令可下发、下行不生效”；WDRR 私有调度器已完成全链路部署并在真实流量下触发运行标记，但 per-AC 加权在 fq 层的架构性局限仍然成立。', size=10)

# ---------- 环境 ----------
h('二、实验环境与拓扑', 1)
table(['项目','配置'],
[
 ['开发板','Bananapi BPI-R4 2.5GE PoE，MT7988A'],
 ['系统','OpenWrt 24.10.0 r28427-6df0e3d02a，内核 6.6.73'],
 ['WiFi','MT7996（BPI-R4-NIC-BE14），2.4G + 5G AP'],
 ['5G AP','phy0.1-ap0，SSID BPI-R4-5G，ch149，HE80，Tx 26 dBm'],
 ['2.4G AP','phy0.0-ap0，SSID BPI-R4，ch11，HE20'],
 ['板端上行','phy0.0-sta0 连接手机热点 Bai（ch11），IP 192.168.140.209，可访问外网'],
 ['PC 有线','192.168.240.2/24 ↔ 板端 br-lan 192.168.240.1'],
 ['PC 无线','MediaTek USB 网卡连接 BPI-R4-5G，IP 192.168.240.126，RSSI −26～−30 dBm'],
 ['打流工具','iperf3 3.17.1（板端 server，PC 端 3.1.3 client，-R 反向即 AP 下行）'],
],
 widths=[3.2,12.2])

para('说明：板端 mt7996e 使用“强制默认 EEPROM”诊断构建（卡内 EEPROM 读取异常时的 workaround），因此绝对吞吐会与完全原厂校准状态略有差异；本文所有对比均为同一构建、同一链路条件下的相对测量。', size=9.5)

# ---------- EDCA ----------
h('三、EDCA 下行参数实时修改', 1)
h('3.1 下发与回读通道', 2)
para('mac80211 的标准路径为：nl80211 SET_WIPHY(WIPHY_TXQ_PARAMS) → ieee80211_set_txq_params() → 更新 link->tx_conf[ac] → drv_conf_tx() → BSS_CHANGED_QOS → mt7996_link_info_changed() → mt7996_mcu_set_tx() → 固件 EDCA_UPDATE。hostapd 只在启动/重载时走这条路径，因此运行中直接改 hostapd.conf 不会生效；本文用自写的静态 C 工具直接发 nl80211 报文，绕过 hostapd。', size=10)
para('回读侧给 mt7996_mcu_set_tx() 增加 last_edca[] 快照，并在 debugfs 暴露 edca 节点，按固件 ACI 顺序（0=BE 1=BK 2=VI 3=VO）打印 raw 值与 fls 指数值。', size=10)

h('3.2 下发工具', 2)
code([
 '// 交叉编译为 aarch64 静态二进制，板端直接运行',
 '/root/edca_set phy0.1-ap0 <AC 0=BE 1=BK 2=VI 3=VO> <aifs> <cwmin> <cwmax> <txop>',
 '# 示例：把 BE 改为激进值',
 '/root/edca_set phy0.1-ap0 0 3 7 15 0',
 '# 回读',
 'cat /sys/kernel/debug/ieee80211/phy0/mt76/edca',
])

h('3.3 回读结果（hostapd 启动后的初始值）', 2)
table(['ACI','aifs','cwmin','cwmax','txop','固件 fls(cwmin/cwmax)'],
[
 ['0 (BE)','3','15','63','0','4 / 6'],
 ['1 (BK)','7','15','1023','0','4 / 10'],
 ['2 (VI)','1','7','15','94','3 / 4'],
 ['3 (VO)','1','3','7','47','2 / 3'],
], widths=[2.2,2.0,2.2,2.2,2.2,4.4])
para('把 BE 改为 aifs=3 / cwmin=7 / cwmax=15 / txop=0 后，同一节点立即回读为 aifs=3 / cwmin=7 / cwmax=15 / txop=0，fls 变为 3/4。写-读之间没有重启 hostapd、没有 down/up 接口。', size=10)

h('3.4 下发时延', 2)
table(['场景','样本','min','p50','p95','max'],
[
 ['连续 50 次切换（无并发打流）','50','147.2 μs','220.3 μs','381.5 μs','884.6 μs'],
 ['20 s 下行打流中每 1 s 切换一次','15','235.8 μs','300.7 μs','550.5 μs','689.0 μs'],
], widths=[6.0,1.6,2.2,2.2,2.2,2.2])
para('时延口径：edca_set 进程内 CLOCK_MONOTONIC，从 sendto(nl80211) 到收到内核 ACK；该 ACK 在 mt7996_mcu_set_tx() 等待固件 EDCA_UPDATE 响应之后才返回，因此包含 host→mac80211→驱动→固件→ACK 的完整往返。', size=9.5)

h('3.5 免重载与业务连续性', 2)
bullets([
 'hostapd 进程 PID 在整个切换过程中保持不变（1919/1867 → 1919/1867）。',
 'STA 的 connected time 从 61 s 连续增长到 76 s，没有 deauth/assoc 事件。',
 '20 s 下行 iperf3：平均 371 Mbit/s，逐秒 343–397 Mbit/s，全程无 0 吞吐空档，Retr=0。',
 '切换 15 次期间没有出现 hostapd “Could not set interface … UP” 或 MCU timeout。',
])
para('结论：EDCA 四参数可以在 AP 运行中实时下发并立即生效，不需要 wifi reload，也不会导致 STA 断连。', size=10, bold=True)

# ---------- A-MPDU ----------
h('四、A-MPDU 聚合窗口实时修改', 1)
h('4.1 实现', 2)
para('在 mt7996_sta 中增加 agg_win_cap 字段，并在 mt7996_mcu_add_tx_ba() 下发 BA TLV 时把 buf_size 截断到 cap；debugfs 的 agg_win_cap 写入时对所有已关联 STA 重放 TX BA（先删后加），从而在不重连的情况下改变固件聚合窗口。0 表示恢复默认窗口。', size=10)
code([
 'cat /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap',
 'echo 2 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap   # 每 A-MPDU 最多 2 个 MPDU',
 'echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap   # 恢复',
])

h('4.2 吞吐结果（5G 下行，10 s，PC→AP 反向 iperf3）', 2)
table(['配置','平均吞吐','逐秒范围','Retr','说明'],
[
 ['cap=0（默认）','381 Mbit/s','363–394','2','基线'],
 ['cap=2','74.3 Mbit/s','63–78','0','聚合被限制为 ≤2 MPDU'],
 ['cap=0（恢复）','402 Mbit/s','387–419','0','写回 0 立即恢复'],
], widths=[3.4,3.0,3.2,1.6,4.8])
para('cap 从 0 改为 2 后吞吐下降 80.5%–81.5%；写回 0 后 10 s 内恢复到 402 Mbit/s。整个过程没有断开 STA、没有重载驱动，dmesg 只出现 “agg_win_cap: cap=2 applied to 2 station(s)” 与 “cap=0 applied to 2 station(s)”。', size=10)
para('注：write 会遍历所有 wcid，因此板端自身连接 Bai 的 STA 也会被一并限制；本机下行测试不受影响，但说明该 debugfs 是“全局 per-device”语义，不是 per-STA。', size=9.5)

# ---------- MCS ----------
h('五、MCS 锁定尝试', 1)
para('实现：mt76.ko 暴露 force_mcs debugfs（0–7 强制 MCS，255 自动），mt76-connac-lib 在 sta_rec_ra_info 组包时覆盖 rx_mcs_bitmask，试图让固件只使用指定 MCS。', size=10)
table(['force_mcs','station tx bitrate','下行吞吐','结果'],
[
 ['0','864.8 Mbit/s HE-MCS8 NSS2','348 Mbit/s（8 s）','未锁到 MCS0'],
 ['1','960.7 Mbit/s HE-MCS9 NSS2','342 Mbit/s（6 s）','未锁到 MCS1'],
 ['255（自动）','960–1080 Mbit/s','371–402 Mbit/s','正常'],
], widths=[2.6,5.2,4.0,4.0])
para('force_mcs 节点可读可写（0/1/255 均回读正确），但 station 的 tx bitrate 与吞吐没有随锁定值变化，dmesg 也没有出现 “mt76: FORCE MCSx”。说明 mt7996 的固件 RC 不消费主机侧 rx_mcs_bitmask（至少 AP 下行路径如此），仅改这个字段无法锁定下行速率。', size=10)
para('结论：MCS“命令可实时下发”成立，但“AP 下行实时生效”不成立；若要真正锁速，需要改固件 RC 的 rate table，或改走 STA 模式/驱动 TX rate 强制路径。', size=10, bold=True)

# ---------- 粒度 ----------
h('六、最小调度粒度', 1)
table(['层','最小粒度','实测/依据'],
[
 ['OpenWrt 软件队列','包 / 帧（skb）','mac80211 fq/txq 以 skb 入队，DRR 以 flow 轮转；quantum 可按 flow 设置'],
 ['固件','MCU 命令 / 帧描述符','EDCA_UPDATE 一次下发 4 个 AC；端到端 147–885 μs，p50 220–301 μs'],
 ['硬件','PPDU / A-MPDU','聚合窗口以 MPDU 为单位；cap=2 时吞吐 402→74.3 Mbit/s'],
], widths=[3.6,4.6,7.6])
para('因此，“实时”在软件层是每个包/每个 flow 可调，在固件层是一次 MCU 命令（百微秒级），在硬件层是一个 PPDU/A-MPDU；不存在比 PPDU 更细的硬件调度粒度。', size=10)

# ---------- WDRR ----------
h('七、私有 WDRR 调度器部署与运行验证', 1)
h('7.1 修改与编译', 2)
para('基于 mac80211 fq 的 DRR 实现，共 5 处修改：fq_flow 增加 quantum；fq_tin_dequeue 按 flow quantum 补充 deficit；fq_flow_init 初始化 quantum=0；tx.c 增加 fq_weight[4] 模块参数；首次 dequeue 时按 txq 的 AC 赋 flow->quantum = fq->quantum × fq_weight[ac]。', size=10)
table(['项目','结果'],
[
 ['编译产物','mac80211.ko，6,603,848 B，md5 49f2aca91f3228adcd83b205f5338d61'],
 ['符号/字符串','fq_weight、__param_fq_weight、private WDRR scheduler active 均在产物中'],
 ['烧录','已覆盖 /lib/modules/6.6.73/mac80211.ko；原厂备份 mac80211.ko.stock（d562…）'],
 ['模块加载','lsmod 正常；/sys/module/mac80211/parameters/fq_weight 存在'],
 ['参数读写','默认 1,1,1,1；echo 4,1,1,1 后回读 4,1,1,1'],
 ['运行标记','dmesg: mac80211: private WDRR scheduler active (fq_weight=1,1,1,1)'],
], widths=[3.2,12.2])

h('7.2 运行验证与架构结论', 2)
para('在真实下行流量下，fq_tin_dequeue_func 被触发，printk_once 打印了 WDRR 标记，证明私有代码路径确实在数据面执行；fq_weight 的写入不需要重载模块，但按当前实现，flow->quantum 只在 flow 首次 dequeue 时赋值，已存在的 flow 不会被后续 sysfs 修改影响。', size=10)
para('架构性结论（历史双 AC 实验，本轮未重复）：mac80211 的 fq 是 per-flow 粒度，AC 级调度发生在 txq 层，同一 txq 内所有 flow 属于同一 AC，因此 per-AC 权重在 fq 层会互相抵消；BE:VO=4:1 时双 AC 吞吐仍约 1:1。要真正改变 AC 优先级，应改 txq 层（airtime fairness 或 ieee80211_txq_schedule），而不是 fq 层。', size=10)

# ---------- 结论 ----------
h('八、总体结论与建议', 1)
bullets([
 'EDCA：运行中直接走 nl80211 下发，百微秒级生效，不需要 wifi reload；hostapd.conf 只在启动/重载时生效，不能用于运行时调节。',
 'A-MPDU：debugfs agg_win_cap 可实时改聚合窗口，吞吐从 402 降到 74.3 Mbit/s，写回 0 立即恢复；适合做聚合敏感型实验。',
 'MCS：force_mcs 节点可写，但 AP 下行速率不变；mt7996 固件 RC 不消费主机 rx_mcs_bitmask，需改固件 rate table 或走 STA 模式。',
 '最小粒度：软件包/帧，固件 MCU 命令，硬件 PPDU/A-MPDU；不存在比 PPDU 更细的硬件粒度。',
 'WDRR：修改→编译→烧录→加载→运行标记已全链路打通；per-AC 加权在 fq 层架构性无效，后续应改 txq 层。',
])
para('建议：① 若目标是把 MCS 锁定做成可交付能力，优先评估固件 RC rate table 或 STA 模式，而不是继续改 rx_mcs_bitmask；② 若目标是 AC 级优先级，直接在 txq/airtime fairness 层做加权，不要继续在 fq 层加权重；③ 当前 mt7996e 使用强制默认 EEPROM，正式交付前应在 EEPROM 正常的板子上复测一遍绝对吞吐。', size=10)

# ---------- 复现 ----------
h('九、关键复现命令', 1)
code([
 '# EDCA 下发 + 回读',
 '/root/edca_set phy0.1-ap0 0 3 7 15 0',
 'cat /sys/kernel/debug/ieee80211/phy0/mt76/edca',
 '',
 '# A-MPDU',
 'echo 2 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap',
 'iperf3 -c 192.168.240.1 -B 192.168.240.126 -t 10 -R -i 2',
 'echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap',
 '',
 '# MCS',
 'echo 0 > /sys/kernel/debug/ieee80211/phy0/mt76/force_mcs',
 'iw dev phy0.1-ap0 station dump | grep "tx bitrate"',
 'echo 255 > /sys/kernel/debug/ieee80211/phy0/mt76/force_mcs',
 '',
 '# WDRR',
 'cat /sys/module/mac80211/parameters/fq_weight',
 'echo 4,1,1,1 > /sys/module/mac80211/parameters/fq_weight',
 'dmesg | grep WDRR',
])

h('十、数据来源与限制', 1)
bullets([
 'EDCA 时延为 edca_set 进程内 CLOCK_MONOTONIC 往返，含内核 ACK 与固件 EDCA_UPDATE 响应；样本 50+15 次。',
 'A-MPDU 吞吐为 10 s 反向 iperf3 平均值；cap=2 与 cap=0 在同一链路、同一 PC 位置连续测得。',
 'MCS 测试中 force_mcs 只在 station 重连后检查，仍未观察到速率变化；不排除需要固件 rate table 才能生效。',
 '板端 mt7996e 为“强制默认 EEPROM”构建，卡内 EEPROM 读取异常；绝对吞吐仅供参考。',
 'WDRR 双 AC 打流为历史实验结论，本轮只验证了模块加载、参数读写与 dmesg 运行标记。',
])

doc.save(OUT)
print("SAVED", OUT)
