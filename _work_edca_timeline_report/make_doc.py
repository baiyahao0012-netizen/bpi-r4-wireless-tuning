# -*- coding: utf-8 -*-
"""生成《无线参数实时下发时序验证实验报告.docx》——EDCA 时序验证 + MCS 实时修改两实验合并版。
全部数据来自 2026-10-20 实测。"""
import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r'D:\Desktop\AI 辅助对话\无线参数实时下发时序验证实验报告.docx'
PNG_EDCA = r'D:\Desktop\AI 辅助对话\_work_timeline\edca_tl_final.png'
PNG_MCS = r'D:\Desktop\AI 辅助对话\_work_timeline\mcs_tl.png'
PNG_AMPDU_TL = r'D:\Desktop\AI 辅助对话\_work_timeline\ampdu_deliver.png'
PNG_AMPDU_HIST = r'D:\Desktop\AI 辅助对话\_work_timeline\ampdu_deliver_hist.png'

BLACK = RGBColor(0, 0, 0)
GRAY_HEAD = 'D9D9D9'


def set_run_font(run, cn='宋体', en='Times New Roman', size=12, bold=False, color=BLACK):
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), cn)


def add_para(doc, text, style='Normal', size=None, align=None, first_indent=True,
             space_before=None, space_after=None, line=1.5):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if first_indent and style == 'Normal':
        p.paragraph_format.first_line_indent = Pt(24)
    if space_before is not None:
        p.paragraph_format.space_before = Pt(space_before)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line
    r = p.add_run(text)
    set_run_font(r, size=size if size else 12)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style='Heading %d' % level)
    p.paragraph_format.space_before = Pt(14 if level == 1 else 11)
    p.paragraph_format.space_after = Pt(6 if level == 1 else 5)
    r = p.add_run(text)
    set_run_font(r, cn='黑体', size=(16 if level == 1 else 14), bold=True)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph(style='Caption')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run(text)
    set_run_font(r, size=10.5)
    return p


def set_cell(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, shade=None):
    if shade:
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), shade)
        tcPr.append(shd)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    set_run_font(r, size=10.5, bold=bold)


def set_table_props(table):
    tblPr = table._tbl.tblPr
    tblPr.append(OxmlElement('w:cantSplit'))
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))
    trPr = table.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement('w:tblHeader')
    th.set(qn('w:val'), 'true')
    trPr.append(th)


def add_footer_page_number(doc):
    sec = doc.sections[0]
    footer = sec.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), ' PAGE ')
    r = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), '21')
    rPr.append(sz)
    r.append(rPr)
    t = OxmlElement('w:t'); t.text = '1'
    r.append(t)
    fld.append(r)
    p._p.append(fld)


def make_table(doc, rows, widths, col_aligns):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.width = widths[j]
            if i == 0:
                set_cell(cell, val, bold=True, shade=GRAY_HEAD)
            else:
                set_cell(cell, val, align=col_aligns[j])
    set_table_props(table)
    return table


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)
    add_footer_page_number(doc)

    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    for sname, sz in (('Title', 18), ('Heading 1', 16), ('Heading 2', 14)):
        st = doc.styles[sname]
        st.font.name = 'Times New Roman'
        st.font.size = Pt(sz)
        st.font.bold = True
        st.font.color.rgb = BLACK
        st.element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')

    # 标题
    tp = doc.add_paragraph(style='Title')
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_after = Pt(18)
    r = tp.add_run('无线参数实时下发时序验证实验报告')
    set_run_font(r, cn='黑体', size=18, bold=True)
    sp = doc.add_paragraph(style='Subtitle')
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sp.paragraph_format.space_after = Pt(12)
    r = sp.add_run('BPI-R4 · MT7996 · 5G AP 下行 · EDCA / MCS / A-MPDU 实时修改 · 2026-10-20')
    set_run_font(r, cn='楷体', size=12)

    # 1 背景与目的
    add_heading(doc, '1 实验背景与目的', 1)
    add_para(doc, '根据 2026-10-16 课题组会议确定的《下一步工作计划·硬件平台方向》，需要“完成 EDCA 实时修改的时序验证实验（同时统计与下发、记录下发时刻），尽快完成聚合（AMPDU）、MCS 等参数的实时修改实验”。会议评审同步提出定量要求：“立即”是定性说法，能否定量测量生效时延，是毫秒级还是微秒级。')
    add_para(doc, '本报告将三个实验合并成文，作为课题组统一维护的实验报告：实验一为 EDCA 实时下发时序验证，实验二为 MCS 速率实时修改时序验证，实验三为 A-MPDU 聚合窗口实时修改时序验证（含驱动侧写入通道的新增）。三个实验均采用同一时序编排口径：一边按秒统计链路吞吐，一边在指定时刻下发参数，实测并记录下发时刻，观察数据何时变化，最终形成时序图。至此会议任务 1 所列 EDCA、MCS、A-MPDU 三项实时修改实验均已完成。')

    # 2 环境与链路
    add_heading(doc, '2 实验环境与链路', 1)
    add_para(doc, '被测设备为 BPI-R4（MT7988A 主控 + MT7996 三频无线，mt7996e 补丁驱动），运行 OpenWrt，内核 6.6.73。被测接口为 5G AP 下行：phy0.1-ap0（SSID BPI-R4-5G，信道 149，HE80，WPA2-PSK），电脑无线网卡以 STA 直连该 AP（实验二记录 station 为 c0:35:32:19:cc:fb，信号约 -39 dBm，链路下行协商速率约 864.8 Mbit/s，HE-MCS8/2 流）。')
    add_para(doc, '工具链路：EDCA 实验使用板端 /root/edca_set.py 通过 nl80211（SET_WIPHY + TXQ_PARAMS）实时下发，并以 /sys/kernel/debug/ieee80211/phy*/mt76/edca 回读固件参数；MCS 实验使用 iw dev phy0.1-ap0 set bitrates 实时下发速率掩码（NL80211 TX rate mask），并以 iw station dump 回读 station 速率；A-MPDU 实验使用驱动侧新增的 debugfs per-station 节点 /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap，写入时直接向固件重放 TX 聚合（STA_REC_BA）TLV，以实时修改聚合窗口（实现细节见 5.1 节），并以 tx_stats 的 Length/Count 分桶回读固件聚合长度分布。三实验均以 iperf3 反向模式打流（板端 server :5201，电脑客户端 -R -i 1），测 AP 下行方向吞吐。时钟对齐方式：以 iperf3 日志中首条每秒行的区间结束时刻（约 1.00s）对齐电脑 perf_counter 原点，使下发时刻与吞吐序列处于同一时钟。')

    # 3 实验一
    add_heading(doc, '3 实验一：EDCA 实时下发时序验证', 1)
    add_heading(doc, '3.1 实验方法', 2)
    add_para(doc, '实验共 100 秒，iperf3 每秒输出 1 个吞吐采样点。打流约第 50 秒下发 BE 激进档（命令：python3 /root/edca_set.py phy0.1-ap0 0 1 3 7 0，目标参数 BE aifs=1、cwmin=3、cwmax=7、txop=0），下发前为默认档（BE aifs=3、cwmin=15、cwmax=63、txop=63）。下发时刻由编排脚本实测记录（目标 50.0s，实测下发窗口 50.000~50.418s，写入事件文件），下发前后各回读一次 debugfs 核对参数命中。全程观察吞吐是否断流、链路是否重连、是否有重传，以及是否需要对 WiFi 执行重载。')
    add_heading(doc, '3.2 下发链路验证：实时生效、免重载', 2)
    add_para(doc, '下发命令返回成功（nl80211 family id = 27，输出 OK: phy0.1-ap0 AC0(BE) aifs=1 cwmin=3 cwmax=7 txop=0）；debugfs 回读精确命中下发参数（BE 固件 cwmin 由 fls=4 变为 fls=2、cwmax 由 fls=6 变为 fls=3），证明参数已写入固件生效。整个 100 秒打流过程中每秒数据点连续无空档，无 AP 重启、无链路重连，iperf3 汇总重传计数为 0，即下发过程无需对 WiFi 执行任何重载操作。')
    add_heading(doc, '3.3 时序图', 2)
    add_para(doc, '图1 为打流开始后 0~100 秒的下行吞吐时序，红色虚线为实测下发时刻 t=50.418s。')
    doc.add_picture(PNG_EDCA, width=Cm(15))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption(doc, '图1 EDCA 激进档实时下发时序（5G AP 下行，t=50.418s 下发）')
    add_heading(doc, '3.4 下发前后统计对比', 2)
    add_para(doc, '下发前段（0~50s）与后段（50~100s）各含 50 个采样点，统计对比如表1 所示。')
    rows1 = [
        ('统计项', '下发前（0~50s）', '下发后（50~100s）', '变化'),
        ('均值（Mbit/s）', '50.0', '51.6', '+1.62（+3.2%）'),
        ('中位数（Mbit/s）', '50.5', '51.8', '+1.3'),
        ('最小值（Mbit/s）', '40.9', '46.2', '—'),
        ('最大值（Mbit/s）', '54.7', '54.9', '—'),
        ('采样点数', '50', '50', '—'),
    ]
    make_table(doc, rows1, [Cm(4.2), Cm(3.8), Cm(3.8), Cm(4.0)],
               [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
    add_caption(doc, '表1 EDCA 下发前后吞吐统计对比')

    # 4 实验二
    add_heading(doc, '4 实验二：MCS 实时修改时序验证', 1)
    add_heading(doc, '4.1 实验方法', 2)
    add_para(doc, '采用与实验一相同的时序编排口径：100 秒反向打流、每秒 1 个采样点，打流约第 50 秒下发 MCS 锁速命令（命令：iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0，将 legacy/HT/VHT/HE 全层速率锁定至最低档），实测下发窗口 50.005~50.253s；打流中回读 station 速率（iw station dump）核对命中，结束后以 iw dev phy0.1-ap0 set bitrates（无参数）清除掩码、恢复自动速率。')
    add_heading(doc, '4.2 下发链路验证：命令实时下发、免重载', 2)
    add_para(doc, '锁速命令在打流中实时下发并返回成功（rc=0），下发窗口 50.005~50.253 秒（毫秒级），全程无断流、无链路重连，无需对 WiFi 执行重载；恢复命令同样实时返回成功。')
    add_heading(doc, '4.3 时序图', 2)
    add_para(doc, '图2 为打流开始后 0~100 秒的下行吞吐时序，红色虚线为实测下发时刻 t=50.253s。')
    doc.add_picture(PNG_MCS, width=Cm(15))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption(doc, '图2 MCS 锁速实时下发时序（5G AP 下行，t=50.253s 下发）')
    add_heading(doc, '4.4 生效性判别：AP 下行速率未受掩码约束', 2)
    add_para(doc, '时序图显示锁速后吞吐无跳变：下发前段均值 49.1 Mbit/s，全程无拐点（变化时刻检测为空），吞吐波动区间 32.2~58.9 Mbit/s；打流中 station 回读速率锁速前后均为 360.3 Mbit/s，未随掩码变化。')
    add_para(doc, '为进一步判别，补做决定性实验：仅下发 legacy-5 6（将下行唯一允许速率锁定为 802.11a 6 Mbit/s）后继续打流 30 秒，吞吐仍维持在 46.1~59.8 Mbit/s 区间、无跳变。若掩码对下行生效，6 Mbit/s 的物理速率无法承载约 50 Mbit/s 的 TCP 吞吐，吞吐必然大幅跌落；实测未跌落，证明速率掩码对 AP 下行发送无约束。')
    add_heading(doc, '4.5 结论与根因', 2)
    add_para(doc, '（1）命令层生效：iw set bitrates 可实时下发、毫秒级完成、免重载，链路行为正常；效果层不生效：对 AP 下行速率无约束，吞吐与 station 回读速率均无变化。')
    add_para(doc, '（2）根因：该命令走 mac80211 的 TX rate mask 机制，但 mt76/mt7996 的 AP 下行速率控制（minstrel_ht 自适应）不消费该掩码——命令被内核接受并返回成功，却未作用于实际发送速率选择。与实验一对比，EDCA 参数经 nl80211/debugfs 直写固件寄存器，因此实时生效；MCS 掩码经 mac80211 速率控制层，在 AP 模式下被忽略。')
    add_para(doc, '（3）认知修正：旧版系统性实测报告引用的“MCS 三段式 960.7、360.3、864.8 MBit/s”实际为 station dump 的瞬时速率波动值，本次实验证明锁速命令并未生效，不应作为锁速生效的证据。')
    add_heading(doc, '4.6 实验局限', 2)
    add_para(doc, '本次未做 2.4G AP 接口对照与 STA 模式验证（板端当前已无 STA 接口，需重搭链路）；mac80211 对 STA 模式接口的速率掩码为标准支持路径，可作为后续生效通道验证方向。')

    # 5 实验三
    add_heading(doc, '5 实验三：A-MPDU 聚合窗口实时修改时序验证', 1)
    add_heading(doc, '5.1 写入通道实现与实验方法', 2)
    add_para(doc, 'A-MPDU 聚合窗口（BA winsize / buf_size）在链路建立阶段由 ADDBA 会话协商确定，运行态没有既有的下发通道，因此本实验先在 mt7996 驱动侧补齐写入接口，再按与实验一相同的时序口径验证。')
    add_para(doc, '写入通道实现：在 mt7996 的 debugfs 目录下新增 per-station 节点 /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap；驱动结构 struct mt7996_sta 增加 agg_win_cap 与 ba_ssn[16] 两个字段，前者为窗口上限值（0 表示不限制），后者记录各 TID 最近一次 TX BA 的起始序号。写入时，对每个已建立聚合的 TID 直接向固件重放 STA_REC_BA TLV（先以 enable=false 撤销、再以 enable=true 重建），并按 agg_win_cap 对 buf_size 执行 clamp，从而把聚合窗口实时改为上限值；写入 0 表示取消限制、恢复默认窗口 256。')
    add_para(doc, '该路径刻意绕开 mac80211 的聚合状态机：AP 下行的 BA 会话因 ADDBA 抖动常处于非 OPERATIONAL，此时 ieee80211_stop_tx_ba_session 会提前返回而不再回调驱动，故只有直接重放固件 TLV 才能保证参数必达。这是本实验能够从“仅有观察能力”升级为“可实时写入”的关键。')
    add_para(doc, '时序口径同实验一：100 秒 iperf3 反向打流、每秒 1 个采样点；打流第 45.183 秒（实测）下发 cap=2，第 75.33 秒下发 cap=0 恢复；无限制段与受限段内各取固件聚合长度分桶快照两次。')
    add_heading(doc, '5.2 下发链路验证：实时下发、免重载、固件侧落地', 2)
    add_para(doc, '节点读写验证：写入（echo 2 > agg_win_cap）返回 rc=0，回读精确命中（输出“c0:35:32:19:cc:fb 2”）。整个 100 秒打流过程无断流、无链路重连，下发与恢复均无需对 WiFi 执行重载。')
    add_para(doc, '固件侧落地证据：内核日志在下发与恢复时各记录一行状态（agg_win_cap: cap=2 applied to 1 station(s) / cap=0 applied to 1 station(s)），表明窗口值已被驱动接受并下发至该站点的 TX 聚合会话。此外，开发期另用带调试打印的探针版本逐档确认了 clamp 后的实际写入值——cap=8、4、2 分别对应 buf_size=8、4、2（tid=0 与 tid=3 均命中），cap=0 时恢复为 buf_size=256；交付版本已移除这些调试打印、仅保留上述一行状态日志，故本节其余结论以固件聚合长度分布与吞吐时序为准。')
    add_heading(doc, '5.3 时序图与三阶段统计', 2)
    add_para(doc, '图3 为打流开始后 0~100 秒的下行吞吐时序，红色虚线为 cap=2 的下发时刻 t=45.183s，橙色点线为 cap=0 的恢复时刻 t=75.33s。')
    doc.add_picture(PNG_AMPDU_TL, width=Cm(15))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption(doc, '图3 A-MPDU 聚合窗口实时下发/恢复时序（5G 下行，t=45.183s 窗口→2，t=75.33s 恢复）')
    add_para(doc, '按无限制段（0~45s）、受限段（46~75s）、恢复段（76~100s）分段统计，结果如表2 所示。受限段中位数 92.0 Mbit/s，相对下发前 185.0 Mbit/s 下降 50.3%；恢复段回到 173.0 Mbit/s，明显高于受限段、与下发前同量级（差异属链路缓变）。以“下发后首个低于前段中位数 60% 的采样点”判定，吞吐变化发生于 t=47.01s（Δ≈1.83s）；恢复后首次抬升发生于 t=77.01s（Δ≈1.68s）。该 Δ 主要受 iperf3 每秒 1 点的采样粒度与 TCP 在途数据限制，并非固件生效时延——固件侧状态日志显示参数在下发瞬间即已写入。')
    rows3 = [
        ('统计项', '无限制段（0~45s）', '受限段 cap=2（46~75s）', '恢复段（76~100s）'),
        ('均值（Mbit/s）', '186.6', '91.2', '171.1'),
        ('中位数（Mbit/s）', '185.0', '92.0', '173.0'),
        ('最小值（Mbit/s）', '129.0', '82.0', '125.0'),
        ('最大值（Mbit/s）', '235.0', '94.8', '215.0'),
        ('采样点数', '45', '29', '24'),
    ]
    make_table(doc, rows3, [Cm(3.4), Cm(4.2), Cm(4.6), Cm(3.8)],
               [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
    add_caption(doc, '表2 A-MPDU 窗口下发/恢复三阶段吞吐统计')
    add_heading(doc, '5.4 固件聚合长度分布（直方图）', 2)
    add_para(doc, '为直接观察固件行为，另取固件侧 A-MPDU 聚合长度分桶统计（tx_stats 的 Length/Count 行，phy band 1）：无限制段取 t=37s 与 t=41s 两次快照、受限段取 t=57s 与 t=61s 两次快照，相邻两次做差即得该 4 秒区间的实际聚合长度分布，如图4。')
    add_para(doc, '无限制段共 2934 个聚合，长度分布覆盖“1”至“56-79”共 8 个桶，其中“2-10”桶最多（756 个），“1”“11-19”“20-28”桶分别为 751、644、451 个，“29-37”“38-46”“47-55”桶依次为 229、59、41 个；受限段（cap=2）共 16869 个聚合，全部落入最小桶“1”，其余各桶计数均为 0。即窗口实时缩小后，固件聚合长度分布整体左移、大聚合桶被清零，发送行为退化为逐 MPDU 发送，与该段吞吐下降 50.3% 相互印证。')
    doc.add_picture(PNG_AMPDU_HIST, width=Cm(15))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption(doc, '图4 A-MPDU 窗口实时下发前后固件聚合长度分布对比（5G 下行）')
    add_heading(doc, '5.5 窗口档位与稳态吞吐的定量关系', 2)
    add_para(doc, '为给出窗口取值的定量影响，另做一次交错扫描：在 72 秒打流中依次切换 cap=8、4、2，并在每个受限档前后各插一段无限制档，以相邻两段无限制档中位数的均值作为该档基准，抵消链路自身的缓变漂移（本次四段无限制档中位数分别为 203.0、207.5、176.0、151.0 Mbit/s）。结果如表3。')
    rows3b = [
        ('窗口档位', '相邻无限制基准（Mbit/s）', '受限段中位数（Mbit/s）', '比值'),
        ('cap=8', '205.2', '230.5', '1.12'),
        ('cap=4', '191.8', '157.0', '0.82'),
        ('cap=2', '163.5', '95.2', '0.58'),
    ]
    make_table(doc, rows3b, [Cm(3.0), Cm(5.0), Cm(5.0), Cm(3.0)],
               [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
    add_caption(doc, '表3 A-MPDU 聚合窗口档位与稳态吞吐（交错扫描）')
    add_para(doc, '可见窗口上限对吞吐的影响并非单调：cap=8 时吞吐与基准相当甚至略高——本链路重传计数达 2000 以上、属易损链路，过长的聚合会因部分 A-MPDU 丢失而浪费空口，适度限制聚合反而中性偏好；cap=4 时下降约 18%；cap=2 时下降约 42%，此时聚合已基本退化为单 MPDU，逐帧空口开销与 BA 交互开销成为主导。即中等窗口处存在折中区间，只有把窗口压到极小时才会带来显著损失。')
    add_heading(doc, '5.6 结论', 2)
    add_para(doc, '（1）通道打通：mt7996 原对 A-MPDU 聚合窗口仅有观察能力（tx_stats 可读），本实验在驱动侧新增 debugfs 写入节点，通过重放固件 STA_REC_BA TLV 实现运行态实时下发，并可随时写回 0 恢复默认窗口。')
    add_para(doc, '（2）真实生效：内核日志显示 cap 值在下发瞬间即被驱动接受并下发至该站点的聚合会话；固件聚合长度分布在 4 秒窗口内由覆盖 1~79 桶整体左移并集中于单 MPDU（该 4 秒内 16869 个聚合全部为单 MPDU）；链路吞吐中位数随之由 185.0 降至 92.0 Mbit/s（−50.3%），恢复后回升到 173.0 Mbit/s，形成可逆的方波式响应。开发期带调试打印的探针版本独立复现了同一现象（184.0 → 93.6 → 225.0 Mbit/s，聚合分布同样由 9 个桶整体左移为全单 MPDU），两版驱动结论一致。')
    add_para(doc, '（3）工程结论：窗口上限对下行吞吐的影响非单调（cap=8 中性偏好、cap=4 约 −18%、cap=2 约 −42%），可作为后续按链路质量动态选择聚合窗口的依据。')

    # 6 总结
    add_heading(doc, '6 总结与会议任务闭环状态', 1)
    add_para(doc, '三个实验的对比汇总如表4 所示。')
    rows4 = [
        ('对比维度', '实验一：EDCA', '实验二：MCS', '实验三：A-MPDU'),
        ('下发通道', 'edca_set.py（nl80211 直写固件）', 'iw set bitrates（TX rate mask）', 'debugfs agg_win_cap（驱动重放 BA TLV）'),
        ('实测下发窗口', '50.000~50.418 s', '50.005~50.253 s', '单次 echo 写入，即时（rc=0）'),
        ('免重载', '是（无重连、Retr 0）', '是（无重连）', '是（无重连、无断流）'),
        ('参数是否生效', '生效（debugfs 回读命中）', '不生效（速率与吞吐无变化）', '生效（固件日志命中 + 聚合分布左移）'),
        ('生效通道', '固件参数直写', '需 STA 模式或驱动补丁', '固件 STA_REC_BA 直写（绕过 mac80211 状态机）'),
        ('吞吐影响', '+3.2%（噪声内，预期）', '无变化（掩码未约束下行）', 'cap=2 中位数 185.0→92.0 Mbit/s（−50.3%）'),
    ]
    make_table(doc, rows4, [Cm(2.4), Cm(4.6), Cm(4.5), Cm(4.5)],
               [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    add_caption(doc, '表4 三项实时下发实验对比')
    add_para(doc, '会议任务 1 闭环状态：EDCA 实时修改的时序验证实验已完成（同时统计与下发、记录下发时刻、形成时序图，并回应评审毫秒/微秒级定量追问）；MCS 实时修改实验已完成（结论为 AP 模式下行不生效，生效需 STA 模式或驱动补丁）；A-MPDU 实时修改实验已完成——在驱动侧新增 debugfs 写入通道，实现聚合窗口的运行态实时下发与可恢复，并以吞吐时序图、固件聚合长度分布与内核下发日志三类证据确认其真实生效。三项实验均按会议要求的同一时序口径（同时统计与下发、记录下发时刻、形成时序图）完成。')
    add_para(doc, '对会议遗留事项的回答：EDCA 参数经固件直写通道即时生效且免重载；MCS 速率掩码命令可实时下发但不约束 AP 下行（软件调度层未消费该掩码）；A-MPDU 聚合窗口原先只有观察通道、无写入通道，本实验通过驱动侧重放固件 BA TLV 补齐，且证明其可实时、确定性落地；OpenWrt 软件队列最小调度粒度已在调度器报告中确认（fq 为 per-flow 粒度、AC 级调度在 txq 层），与此处“掩码被 mac80211 调度层接受但不影响驱动速率选择”相互印证。')

    # 7 数据与复现
    add_heading(doc, '7 数据与复现', 1)
    add_para(doc, '实验一数据与复现：数据文件位于 _work_timeline 目录（edca_tl_final_iperf3.txt 为 100 个每秒吞吐点，edca_tl_final_events.json 记录实测下发时刻与 EDCA 下发前后值）；先在板端拉起 iperf3 server（iperf3 -s -p 5201 -D），再在电脑执行 python run_edca_timeline.py --issue-sec 50 --duration 100 --out-prefix edca_tl_final --iperf3 D:\\Download\\iperf3.22_64\\iperf3.22\\iperf3.exe。')
    add_para(doc, '实验二数据与复现：数据文件位于 _work_timeline 目录（mcs_tl_iperf3.txt、mcs_tl_events.json 记录实测下发时刻与锁速前后 station 速率）；复现命令为 python run_mcs_timeline.py --station c0:35:32:19:cc:fb --issue-sec 50 --duration 100 --out-prefix mcs_tl。')
    add_para(doc, '实验三数据与复现：数据文件位于 _work_timeline 目录（ampdu_deliver_iperf3.txt 为 100 个每秒吞吐点，ampdu_deliver_events.json 记录实测下发时刻、三阶段固件聚合长度分桶快照与内核下发日志，ampdu_deliver.png 为时序图，ampdu_deliver_hist.png 为聚合长度分布对比图；开发期探针版本对应 ampdu_v2_* 一组文件，结论一致，可作可复现性佐证）；复现命令为 python ampdu_final.py --cap 2 --issue-sec 45 --duration 100 --out-prefix ampdu_deliver。交付的驱动模块为去调试打印版本 mt7996e-ampdu.ko（md5 f714dd0b58b7d8add687706935312a22），已烧录板端验证，载入后即以 /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap 提供写入通道。')
    add_para(doc, '共同注意事项：电脑侧 iperf3 需使用 3.2 及以上版本（3.1.3 不支持 --forceflush 参数）；三个实验结束后均已恢复初始状态（EDCA 恢复默认档、MCS 速率掩码已清除、A-MPDU 窗口已写回 0 恢复默认 256）。实验期间必须保证“一条网卡连 BPI-R4-5G 用于打流与 SSH、另一条网卡连外部网络用于上网”的双网卡拓扑（本实验为 WLAN 连 BPI-R4-5G、WLAN 3 连 DianGroup103）。')

    doc.save(OUT)
    print('SAVED:', OUT)


if __name__ == '__main__':
    main()
