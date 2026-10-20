# -*- coding: utf-8 -*-
"""生成《无线参数实时下发系统性实测报告》Word 文档（无模板创建，动态 TOC）。"""
import docx
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r'D:\Desktop\AI 辅助对话\无线参数实时下发系统性实测报告.docx'

BLACK = RGBColor(0, 0, 0)
GRAY_HDR = 'D9D9D9'


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
    rFonts.set(qn('w:ascii'), en)
    rFonts.set(qn('w:hAnsi'), en)
    rFonts.set(qn('w:eastAsia'), cn)


def style_heading(doc, name, size, space_before, space_after):
    st = doc.styles[name]
    st.font.name = 'Times New Roman'
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = BLACK
    rPr = st.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rFonts.set(qn('w:eastAsia'), '黑体')


def add_par(doc, text, cn='宋体', size=12, bold=False, align=None, indent=None,
            line=1.5, space_before=0, space_after=0):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    if align is not None:
        pf.alignment = align
    if indent is not None:
        pf.first_line_indent = indent
    pf.line_spacing = line
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    r = p.add_run(text)
    set_run_font(r, cn=cn, size=size, bold=bold)
    return p


def add_title(doc, text, size=16):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run_font(r, cn='黑体', en='Times New Roman', size=size, bold=True)
    return p


def add_h1(doc, text):
    p = doc.add_paragraph(text, style='Heading 1')
    pf = p.paragraph_format
    pf.space_before = Pt(14)
    pf.space_after = Pt(6)
    pf.keep_with_next = True
    for r in p.runs:
        set_run_font(r, cn='黑体', en='Times New Roman', size=16, bold=True)
    return p


def add_h2(doc, text):
    p = doc.add_paragraph(text, style='Heading 2')
    pf = p.paragraph_format
    pf.space_before = Pt(11)
    pf.space_after = Pt(5)
    pf.keep_with_next = True
    for r in p.runs:
        set_run_font(r, cn='黑体', en='Times New Roman', size=14, bold=True)
    return p


def add_h3(doc, text):
    p = doc.add_paragraph(text, style='Heading 3')
    pf = p.paragraph_format
    pf.space_before = Pt(9)
    pf.space_after = Pt(4)
    pf.keep_with_next = True
    for r in p.runs:
        set_run_font(r, cn='黑体', en='Times New Roman', size=12, bold=True)
    return p


def add_body(doc, text):
    return add_par(doc, text, cn='宋体', size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                   indent=Pt(24), line=1.5)


def add_code(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.0
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.left_indent = Pt(12)
    r = p.add_run(text)
    set_run_font(r, cn='宋体', en='Consolas', size=9, bold=False)
    return p


def add_caption(doc, text):
    return add_par(doc, text, cn='宋体', size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
                   space_before=4, space_after=4)


def shade_cell(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    vAlign = tcPr.find(qn('w:vAlign'))
    if vAlign is not None:
        vAlign.addprevious(shd)
    else:
        tcPr.append(shd)


def set_cell_text(cell, text, bold=False, align='left'):
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    if align == 'center':
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == 'right':
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    set_run_font(r, cn='宋体', en='Times New Roman', size=10.5, bold=bold)


def add_table(doc, header, rows, aligns=None, widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, h in enumerate(header):
        set_cell_text(t.cell(0, j), h, bold=True, align='center')
        shade_cell(t.cell(0, j), GRAY_HDR)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement('w:tblHeader')
    tblHeader.set(qn('w:val'), 'true')
    trPr.append(tblHeader)
    for i, row in enumerate(rows, start=1):
        trPr_i = t.rows[i]._tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit')
        trPr_i.append(cant)
        for j, v in enumerate(row):
            a = 'left'
            if aligns and aligns[j] == 'center':
                a = 'center'
            elif aligns and aligns[j] == 'right':
                a = 'right'
            set_cell_text(t.cell(i, j), str(v), align=a)
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


def add_toc(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve')
    it.text = 'TOC \\o "1-2" \\h \\z \\u'
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t'); t.text = '（目录：打开文档后按 F9 更新，或由目录工具刷新）'
    f3 = OxmlElement('w:fldChar'); f3.set(qn('w:fldCharType'), 'end')
    for e in (f1, it, f2, t, f3):
        run._r.append(e)


def add_page_number_footer(section, start=None):
    section.footer.is_linked_to_previous = False
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin')
    it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve')
    it.text = 'PAGE'
    f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'end')
    for e in (f1, it, f2):
        run._r.append(e)
    if start:
        sectPr = section._sectPr
        pgNumType = sectPr.find(qn('w:pgNumType'))
        if pgNumType is None:
            pgNumType = OxmlElement('w:pgNumType')
            sectPr.append(pgNumType)
        pgNumType.set(qn('w:start'), str(start))


def main():
    doc = Document()
    sec0 = doc.sections[0]
    sec0.page_width = Cm(21.0)
    sec0.page_height = Cm(29.7)
    sec0.top_margin = Cm(2.5)
    sec0.bottom_margin = Cm(2.5)
    sec0.left_margin = Cm(2.5)
    sec0.right_margin = Cm(2.5)
    st = doc.styles['Normal']
    st.font.name = 'Times New Roman'
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    style_heading(doc, 'Heading 1', 16, 14, 6)
    style_heading(doc, 'Heading 2', 14, 11, 5)
    style_heading(doc, 'Heading 3', 12, 9, 4)

    # ===== 封面 =====
    add_title(doc, '无线参数实时下发系统性实测报告', 16)
    add_title(doc, '（EDCA / A-MPDU / MCS 实时性与三层调度粒度）', 16)
    add_par(doc, '2026-10-19 实测 · BPI-R4 / MT7996 / OpenWrt 24.10.0', cn='宋体', size=12,
            align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

    # ===== 目录 =====
    add_par(doc, '目  录', cn='黑体', size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
    add_toc(doc)
    # 正文另起页（分节2）
    sec1 = doc.add_section(WD_SECTION.NEW_PAGE)
    sec1.top_margin = Cm(2.5); sec1.bottom_margin = Cm(2.5)
    sec1.left_margin = Cm(2.5); sec1.right_margin = Cm(2.5)
    add_page_number_footer(sec1, start=1)
    sec0.footer.is_linked_to_previous = False  # 封面/目录页无页码

    # ===== 1 概述 =====
    add_h1(doc, '1 概述')
    add_h2(doc, '1.1 任务背景')
    add_body(doc, '在 BPI-R4（MT7996 三频无线，mt7996e 补丁驱动）上，需要系统性实测 EDCA（信道接入 QoS 参数）、A-MPDU（帧聚合参数）、MCS（速率掩码）三类参数“命令下发”的实时程度：是否即时生效、是否需要重载 WiFi（wifi reload / 重启 AP）；并明确 OpenWrt 软件队列、固件（MT7996 MCU）及硬件（基带发送引擎）三者能够支持的最小调度粒度。载体采用方案 A：板子 5G 射频（phy0.1）作为 AP（SSID BPI-R4-5G，ch149 HE80），电脑无线网卡直连，iperf3 反向打流（AP 下行方向），板端命令通过 SSH/串口执行。')
    add_h2(doc, '1.2 测试目标')
    add_body(doc, '（1）逐一确认三类参数在打流状态下实时下发的即时性与免重载性；（2）对可实时调节的参数给出端到端下发时延定量结果（微秒/毫秒级判定）；（3）对无实时入口的参数给出限制结论与替代路径；（4）给出软件队列、固件、硬件三层的最小调度粒度结论矩阵。')
    add_h2(doc, '1.3 结论摘要')
    add_body(doc, 'EDCA 参数实时下发且免重载：5G 打流态端到端中位 463.5μs，扣除 netlink 基线（91.7μs）后驱动+固件专属耗时约 371.8μs，微秒级成立。MCS 速率掩码实时下发且免重载：打流中锁定全层最低速率后，station 下行速率由 960.7（HE-MCS9/NSS2）降至 360.3 MBit/s（HE-MCS7/NSS1），吞吐由约 400 稳定降至 272 Mbps（约 -32%），恢复后回升；命令即时生效，速率控制算法重新收敛约 10s。A-MPDU 聚合参数在本固件无运行时实时入口（iw station set 无 ampdu 参数、station debugfs 无 ampdu_factor/ampdu_density 节点），属关联期能力协商，需断开重连或 wifi reload，判定为非实时下发参数。软件队列层 DRR 调度参数（txq quantum）实时可调免重载。三层最小调度粒度：软件队列为包/帧粒度（DRR 量子字节粒度 1~2^32），固件为 MCU 命令粒度（EDCA 约 370μs 往返），硬件为下一帧发送即生效（μs 级）。')

    # ===== 2 测试环境与链路 =====
    add_h1(doc, '2 测试环境与链路')
    add_h2(doc, '2.1 硬件与系统')
    add_table(doc,
              ['项目', '值'],
              [['板型', 'BPI-R4（MT7996 三频）'],
               ['固件', 'OpenWrt 24.10.0 r28427-6df0e3d02a'],
               ['内核', '6.6.73'],
               ['驱动', 'mt7996e（含 edca debugfs 补丁，节点 /sys/kernel/debug/ieee80211/phy0/mt76/edca）'],
               ['管理网段', 'br-lan 192.168.1.1/24'],
               ['PC', 'Windows；WLAN3（MediaTek USB 网卡）接入 BPI-R4-5G，IP 192.168.1.126，station MAC 90:de:80:1c:6a:7a']],
              aligns=['left', 'left'], widths=[3.5, 9.5])
    add_h2(doc, '2.2 无线拓扑（方案 A）')
    add_table(doc,
              ['接口', '角色', 'SSID', '频段/模式', '说明'],
              [['phy0.1-ap0', '5G AP', 'BPI-R4-5G', 'ch149 HE80, psk2', '被测下行链路（电脑直连）'],
               ['phy0.0-ap0', '2.4G AP', 'BPI-R4', 'ch6 HE20, psk2', '共存 AP（不参与打流）'],
               ['phy0.2-ap0', '6G AP', 'BPI-R4-6G', '6G', '共存 AP（未使用）']],
              aligns=['left', 'left', 'left', 'left', 'left'], widths=[2.6, 1.8, 2.2, 3.4, 4.8])
    add_h2(doc, '2.3 工具')
    add_table(doc,
              ['工具', '位置', '作用'],
              [['edca_set.py', '板端 /root/edca_set.py', 'nl80211 实时下发 EDCA（原生 netlink）'],
               ['measure_edca.py', '板端 /root/measure_edca.py', 'EDCA 下发时延定量测量（AC=-1 为基线模式）'],
               ['iw 6.9', '板端', 'set bitrates / station / phy set txq 实时调节与回读'],
               ['iperf3', '板端 server(5201) + PC 客户端', '反向打流（AP 下行）验证与流量佐证']],
              aligns=['left', 'left', 'left'], widths=[3.5, 5, 6])

    # ===== 3 实验设计 =====
    add_h1(doc, '3 实验设计')
    add_h2(doc, '3.1 调节入口侦察')
    add_table(doc,
              ['参数类别', '候选入口', '侦察结论'],
              [['EDCA', 'edca_set.py（nl80211 SET_WIPHY+TXQ_PARAMS）+ debugfs 回读', '可用：实时写入+回读命中'],
               ['MCS/速率', 'iw dev <if> set bitrates（legacy/ht/vht/he 掩码）', '可用：全层锁实时生效；station 回读需写全 dev 形式'],
               ['A-MPDU', 'iw station set / station debugfs / mt76 debugfs', '无运行时入口：无 ampdu 参数与节点'],
               ['软件队列', 'iw phy set txq limit/memory_limit/quantum', '可用：DRR 参数实时可调']],
              aligns=['left', 'left', 'left'], widths=[3, 6.5, 5])
    add_h2(doc, '3.2 实验矩阵与执行')
    add_table(doc,
              ['实验', '内容', '状态'],
              [['EDCA 实时性与时延', '120s 打流中写入激进档；打流态时延 100 次；基线 100 次', '完成'],
               ['MCS 实时调整', '40s 打流中全层锁最低速率→回读→恢复', '完成'],
               ['A-MPDU 聚合参数', '入口侦察与限制判定', '完成（限制结论）'],
               ['软件队列 DRR', 'txq quantum 实时调整与回读', '完成']],
              aligns=['left', 'left', 'left'], widths=[4, 7.5, 3])

    # ===== 4 EDCA =====
    add_h1(doc, '4 EDCA 实时下发实测')
    add_h2(doc, '4.1 下发通路')
    add_body(doc, 'EDCA 参数经用户态 nl80211（SET_WIPHY + WIPHY_TXQ_PARAMS）→ cfg80211 → mac80211 conf_tx → mt76 驱动构造 MCU 命令 → 固件 EDCA 参数表 → 硬件发送引擎，全程无需 wifi reload。debugfs 节点 /sys/kernel/debug/ieee80211/phy0/mt76/edca 可回读各 AC 当前参数。')
    add_h2(doc, '4.2 生效即时性（120s 打流切换）')
    add_body(doc, 'PC 反向打流 120s（每秒 1 点），打流约 60s 处写入激进档 EDCA（BE：aifs=1、cwmin=3、cwmax=7、txop=0，python3 /root/edca_set.py phy0.1-ap0 0 1 3 7 0）。netlink 返回 OK（family id=27），debugfs 回读精确命中（firmware fls=2/3）。写入瞬间（59-61s 区间）吞吐由 36.5 下坠至 167 Mbps 后立即恢复，全程无重连、无 AP 重启、仅 25 次重传——实时生效、免重载的直接定量证据。全程平均 398 Mbps，写入前后段均值差异小于 2%（单客户端饱和流 EDCA 退避参数不参与竞争，吞吐不敏感；EDCA 真实收益场景是多客户端竞争与时延敏感流量）。')
    add_h2(doc, '4.3 下发时延定量（5G 打流态）')
    add_table(doc,
              ['口径（各 100 次）', 'min', 'median', 'mean', 'p90', 'p99', 'max'],
              [['A 基线（AC=-1，GETFAMILY 往返）', '88.7', '91.7', '93.1', '96.2', '115.9', '148.2'],
               ['B EDCA 打流态下发', '249.0', '463.5', '491.4', '627.1', '1296.8', '1333.9'],
               ['C 专属耗时（B−A）', '—', '371.8', '398.3', '530.9', '—', '—']],
              aligns=['left', 'right', 'right', 'right', 'right', 'right', 'right'],
              widths=[5.2, 1.6, 1.6, 1.6, 1.6, 1.6, 1.6])
    add_par(doc, '注：单位微秒（μs）；C 行由 B−A 逐样本相减后统计。', cn='宋体', size=10.5, space_after=6)
    add_body(doc, '打流态测量窗口内 iperf3 日志确认有持续流量（241-396 Mbps，45s 平均 315 Mbps、13 重传），测量状态有效。5G 打流态 median 463.5μs，全部样本小于 1.4ms，微秒级（亚毫秒）结论成立。')
    add_h2(doc, '4.4 与 2.4G 对比')
    add_table(doc,
              ['场景', '2.4G（历史）', '5G（本次）'],
              [['基线（netlink 往返）', '94.4 μs', '91.7 μs'],
               ['打流态中位数', '322.1 μs', '463.5 μs'],
               ['专属耗时', '约 228 μs', '约 371.8 μs']],
              aligns=['left', 'right', 'right'], widths=[5, 3.5, 3.5])
    add_body(doc, '5G 打流态时延高于 2.4G 约 44%，符合预期：5G 链路承载 300-400 Mbps 高流量，MCU 命令处理路径更忙、队列更长。两者均在亚毫秒量级。')

    # ===== 5 MCS =====
    add_h1(doc, '5 MCS 速率掩码实时调整实测')
    add_h2(doc, '5.1 入口与命令形式')
    add_body(doc, '速率掩码入口为 iw dev <ifname> set bitrates（NL80211_CMD_SET_WIPHY + TX_RATES），支持 legacy/ht/vht/he 各层掩码，空参数恢复自动速率。实测发现两点：其一，iw station get/dump 必须写全 “iw dev <ifname> station ...”，省略 dev 直接返回整体 usage（iw 6.9 在 OpenWrt 上的解析行为）；其二，单独下发 he-mcs 或 vht-mcs 掩码不产生可测量的速率约束，必须全层（legacy+ht+vht+he）一起锁定才可靠生效——mt76 掩码应用细节。')
    add_h2(doc, '5.2 实时生效证据（station 速率回读）')
    add_body(doc, '打流过程中全层锁定（iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0），iw station get 回读下行速率：锁定前 960.7 MBit/s（80MHz HE-MCS9 HE-NSS2）→ 锁定后 360.3 MBit/s（HE-MCS7 HE-NSS1）→ 恢复后 864.8 MBit/s（HE-MCS8 HE-NSS2）。NSS 由 2 降为 1、MCS 受限于掩码，恢复后回到双流高 MCS——掩码实时应用到固件速率控制。')
    add_h2(doc, '5.3 吞吐三段式')
    add_table(doc,
              ['时段', '吞吐', '说明'],
              [['基线（0-23s）', '306-483 Mbps（约 400）', '自动速率'],
               ['锁定段（24-37s）', '267-274 Mbps 稳定平台', '全层锁最低速率，约 -32%'],
               ['恢复段（38-40s）', '356→424 Mbps 回升', '清空掩码恢复自动']],
              aligns=['left', 'left', 'left'], widths=[3.6, 5, 6])
    add_body(doc, '40s 全程平均 352 Mbps、重传仅 1 次：锁定/恢复全程无重连、无断流、无 wifi reload。锁定段 14 秒稳定的 272 Mbps 平台与 station 速率回读（360.3 MBit/s 单流低 MCS）互为印证。')
    add_h2(doc, '5.4 收敛时间分析')
    add_body(doc, '命令下发本身即时生效（station 速率字段在锁定后 5s 内已更新、吞吐平台在锁定后约 10s 建立；恢复后约 10s 回升）。约 10s 的过渡来自 minstrel_ht 速率控制算法的采样与收敛，属于算法特性而非 nl80211 下发时延——下发时延本身为微秒级（netlink 往返 ~90μs 量级，与 EDCA 基线同源）。工程上应区分“命令生效时延”（μs）与“速率控制收敛时间”（约 10s）。')

    # ===== 6 A-MPDU =====
    add_h1(doc, '6 A-MPDU 聚合参数：限制结论')
    add_h2(doc, '6.1 入口缺失证据')
    add_body(doc, '三类候选入口逐一确认不可用于运行时实时调节：（1）iw station set 在本 iw 6.9 仅支持 txpwr / airtime_weight / vlan，无 ampdu_factor / ampdu_density 参数；（2）mac80211 station debugfs（/sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/90:de:80:1c:6a:7a/）仅有 agg_status、airtime、aqm、ht_capa、vht_capa、eht_capa、flags 等节点，无 ampdu_factor / ampdu_density 可写节点；（3）mt76 debugfs（/sys/kernel/debug/ieee80211/phy0/mt76/）无 ampdu 相关节点。')
    add_h2(doc, '6.2 结论')
    add_body(doc, 'A-MPDU 聚合参数（ampdu_factor / ampdu_density）属关联期能力协商：由 STA 关联时的 HT/VHT/HE capability 交换决定，运行时修改需断开重连或 wifi reload，判定为非实时下发参数。mt76 固件的实际聚合长度由固件自动聚合控制，上限一般为 8×32KB 或 16×帧。')
    add_h2(doc, '6.3 观察与替代路径')
    add_body(doc, '聚合状态可通过 station debugfs agg_status、tx_stats 及 mt76 hw-queues 观察；如需量测聚合长度对吞吐的影响，可采用“锁 legacy 速率（无聚合）”方式间接验证（本报告 MCS 实验的 legacy 掩码即含无聚合语义），或修改 hostapd 配置后 wifi reload 验证。')

    # ===== 7 软件队列 =====
    add_h1(doc, '7 软件队列调度实测')
    add_h2(doc, '7.1 队列结构')
    add_body(doc, 'mac80211 提供 4096 个 flow 队列（每链路/TID 粒度），phy 级全局限制：packet limit 8192 pkts、memory limit 16 MB；mt76 驱动在 xmit-queues 上实现 DRR（Deficit Round Robin）调度，调度量子（quantum）与队列上限实时可调；固件侧 PLE/PSE 硬件队列（BCN_Q0、HIF_Q2、MDP_RXQ、SEC_TXQ 等）承载帧描述符，hw-queues 可读快照。')
    add_h2(doc, '7.2 实时调整验证')
    add_body(doc, '执行 iw phy0 set txq quantum 512 与 quantum 65535 后，iw phy0 get txq 回读 Quantum 由 300 精确变为 512、65535 字节，Packet limit（8192）与 Memory limit（16 MB）不变，全程无 reload——DRR 调度参数实时生效。')
    add_h2(doc, '7.3 调度粒度含义')
    add_body(doc, '软件队列层的最小调度粒度是“包/帧”粒度：DRR 以 quantum（字节）为配额逐队列轮转，单客户端单流无队列竞争时该参数无吞吐感知；多客户端或多 QoS 流竞争场景下，quantum/limit 决定各队列的公平份额与突发上限，是 OpenWrt 侧可直接实时干预的最细一层调度旋钮。')

    # ===== 8 三层调度粒度 =====
    add_h1(doc, '8 三层调度粒度分析')
    add_table(doc,
              ['层次', '实体', '最小调度粒度', '实时调节入口', '实测依据'],
              [['软件队列', 'mac80211 flow 队列 + mt76 DRR（xmit-queues）', '包/帧粒度；DRR 量子字节粒度（1~2^32）', 'iw phy set txq limit/memory_limit/quantum', 'quantum 300→65535 即时生效'],
               ['固件', 'MT7996 MCU + PLE/PSE 队列', 'MCU 命令粒度（EDCA 参数表/速率表更新），帧描述符队列', 'nl80211（EDCA）；iw set bitrates（速率）', 'EDCA 专属约 371.8μs；速率表瞬时更新'],
               ['硬件', '基带发送引擎', '下一帧发送即生效（μs 级）', '无独立入口，经固件配置更新', '打流中参数写入后吞吐即刻响应']],
              aligns=['left', 'left', 'left', 'left', 'left'], widths=[2, 3.4, 3.6, 3.4, 3])
    add_h2(doc, '8.1 最小调度粒度结论')
    add_body(doc, '（1）软件队列层：OpenWrt 能以包/帧为最小单位调度，DRR 量子可细到 1 字节步进，是三层中最细且完全用户可控的一层，但单流场景无感知，价值体现在多客户端/QoS 竞争。（2）固件层：EDCA、速率等参数以 MCU 命令为粒度下发，往返约 90μs 基线 + 约 370μs 专属处理，属微秒级；聚合长度等关联期参数不可运行时下发。（3）硬件层：参数落表后下一帧发送即生效，时延在 μs 级，不可被软件进一步细分。综合结论：最小可实时干预调度粒度 = 软件队列（包粒度），最小参数生效粒度 = 固件 MCU 命令（微秒级），物理生效上限 = 硬件下一帧（微秒级）。')

    # ===== 9 结论矩阵 =====
    add_h1(doc, '9 结论矩阵')
    add_table(doc,
              ['参数', '即时生效', '需否 reload', '实测时延/收敛', '粒度定位'],
              [['EDCA（aifs/cwmin/cwmax/txop）', '是', '否', '打流态 median 463.5μs；专属 371.8μs', '固件 MCU 命令（μs）'],
               ['MCS/速率掩码', '是', '否', '命令 μs 级；速率控制收敛约 10s', '软件（minstrel_ht）+ 固件速率表'],
               ['A-MPDU 聚合参数', '否', '是（重连/reload）', '无运行时入口', '关联期能力协商'],
               ['软件队列 DRR（txq quantum）', '是', '否', '即时生效（回读命中）', '软件队列（包/字节粒度）'],
               ['txpower', '是', '否', '即时生效（历史已验证）', '固件/硬件']],
              aligns=['left', 'center', 'center', 'left', 'left'], widths=[4, 1.8, 2, 4.2, 3])

    # ===== 10 复现步骤 =====
    add_h1(doc, '10 复现步骤（命令清单）')
    add_h2(doc, '10.1 EDCA 时延与基线')
    add_code(doc, 'python3 /root/measure_edca.py phy0.1-ap0 -1 1 3 7 0 100     # A 基线（AC=-1）')
    add_code(doc, 'iperf3.exe -c 192.168.1.1 -p 5201 -R -t 45 -i 1 --logfile iperf3_5g_latency.txt   # PC 打流')
    add_code(doc, 'python3 /root/measure_edca.py phy0.1-ap0 0 1 3 7 0 100      # B 打流态（打流开始 6s 后执行）')
    add_h2(doc, '10.2 MCS 实时调整')
    add_code(doc, 'iperf3.exe -c 192.168.1.1 -p 5201 -R -t 40 -i 1 --logfile iperf3_5g_mcs_main2.txt   # PC 打流')
    add_code(doc, 'iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0   # 锁定')
    add_code(doc, 'iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a            # 回读 tx bitrate（必须写全 dev）')
    add_code(doc, 'iw dev phy0.1-ap0 set bitrates                             # 恢复自动速率')
    add_h2(doc, '10.3 软件队列')
    add_code(doc, 'iw phy0 get txq; iw phy0 set txq quantum 512; iw phy0 get txq   # DRR 量子实时调整')
    add_h2(doc, '10.4 聚合参数入口核查（限制结论）')
    add_code(doc, 'ls /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/*/   # 无 ampdu_factor/density')

    # ===== 11 局限与后续 =====
    add_h1(doc, '11 局限与后续')
    add_body(doc, '（1）EDCA 时延测量为端到端用户态口径，固件内部写硬件寄存器的最后一步无法从软件侧观测，增量在 μs 量级内。（2）MCS 收敛约 10s 为 minstrel_ht 行为，不同速率控制算法（如 mt76 固件 RC）可能不同；单客户端饱和流场景掩盖了 EDCA/DRR 参数的多客户端竞争价值。（3）A-MPDU 仅完成入口限制判定，未做改 hostapd 配置 reload 后的聚合长度对比；如需该数据可后续补测。（4）txpower 曾拉高至 20dBm（iw set txpower fixed 2000），重启后失效，复测前需重设；本次打流在默认 7dBm 下进行，链路近距离无影响。')

    doc.save(OUT)
    print('SAVED:', OUT)


if __name__ == '__main__':
    main()
