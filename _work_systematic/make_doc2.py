# -*- coding: utf-8 -*-
"""生成《无线参数实时下发系统性实测报告》Word 文档（无模板创建，动态 TOC）。"""
import docx
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r'D:\Desktop\kaggle\EDCA恢复材料\无线参数实时下发系统性实测报告.docx'

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


def style_heading(doc, name, cn_font, size, bold=True):
    st = doc.styles[name]
    st.font.name = 'Times New Roman'
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.color.rgb = BLACK
    rPr = st.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rFonts.set(qn('w:eastAsia'), cn_font)


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


def add_title(doc, text, size=18):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run_font(r, cn='黑体', en='Times New Roman', size=size, bold=True)
    return p


def add_h1(doc, text):
    p = doc.add_paragraph(style='Heading 1')
    pf = p.paragraph_format
    pf.space_before = Pt(14)
    pf.space_after = Pt(6)
    pf.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, cn='黑体', en='Times New Roman', size=16, bold=True)
    return p


def add_h2(doc, text):
    p = doc.add_paragraph(style='Heading 2')
    pf = p.paragraph_format
    pf.space_before = Pt(11)
    pf.space_after = Pt(5)
    pf.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, cn='黑体', en='Times New Roman', size=14, bold=True)
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


def add_page_break(doc):
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def add_toc(doc):
    """插入动态 TOC 域（Heading 1-2）。"""
    p = doc.add_paragraph()
    r = p.add_run()
    fldChar = OxmlElement('w:fldChar')
    fldChar.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'TOC \\o "1-2" \\h \\z \\u'
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t')
    t.text = '（目录：请在 Word 中按 F9 或使用“引用-更新目录”刷新）'
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    r._element.append(fldChar)
    r._element.append(instrText)
    r._element.append(fldChar2)
    r._element.append(t)
    r._element.append(fldChar3)
    return p


def add_page_number_footer(doc):
    """正文节页脚居中页码域。"""
    footer = doc.sections[-1].footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    fldChar = OxmlElement('w:fldChar')
    fldChar.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'PAGE'
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')
    r._element.append(fldChar)
    r._element.append(instrText)
    r._element.append(fldChar2)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)
    st = doc.styles['Normal']
    st.font.name = 'Times New Roman'
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    style_heading(doc, 'Heading 1', '黑体', 16)
    style_heading(doc, 'Heading 2', '黑体', 14)

    # ===== 节1：封面 + 目录（无页码） =====
    add_title(doc, '无线参数实时下发系统性实测报告', 18)
    add_par(doc, '—— EDCA / A-MPDU / MCS 实时性实测与三层调度粒度分析', cn='宋体', size=12,
            align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_par(doc, '（BPI-R4 · OpenWrt 24.10.0 r28427 · 内核 6.6.73 · 2026-10-19 实测）',
            cn='宋体', size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)
    add_h1(doc, '目录')
    add_toc(doc)

    # ===== 节2：正文（页码从 1 起） =====
    sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
    sec2.page_width = Cm(21.0)
    sec2.page_height = Cm(29.7)
    sec2.top_margin = Cm(2.5)
    sec2.bottom_margin = Cm(2.5)
    sec2.left_margin = Cm(2.5)
    sec2.right_margin = Cm(2.5)
    sec2.footer.is_linked_to_previous = False
    add_page_number_footer(doc)

    # ===== 1 概述 =====
    add_h1(doc, '1 概述')
    add_h2(doc, '1.1 任务背景')
    add_body(doc, '为回答“无线参数命令下发是否即时生效、是否需要重载 WiFi、OpenWrt 软件队列/固件/硬件三者能支持的最小调度粒度”这一问题，本报告对 EDCA、A-MPDU、MCS 三类参数在 BPI-R4（mt7996e 补丁驱动）上的实时下发能力进行系统性实测，并对软件队列、固件、硬件三层的调度粒度作出分析与定位。')
    add_h2(doc, '1.2 测试目标')
    add_body(doc, '（1）验证 EDCA 参数实时下发的端到端时延并记录下发时刻与统计；（2）实测 MCS 速率掩码在打流过程中的实时切换效果；（3）核实 A-MPDU 聚合参数是否存在运行时调节入口；（4）验证软件队列 DRR 参数的实时可调性；（5）给出三层最小调度粒度结论。')
    add_h2(doc, '1.3 结论摘要')
    add_body(doc, 'EDCA 与 MCS 均为“即时生效、免重载”：EDCA 打流态下发中位时延 463.5μs，扣除基线 91.7μs 后驱动+固件专属耗时 371.8μs，写入瞬间吞吐短暂下坠即恢复、全程无断流；MCS 全层速率掩码锁定后 station 下行速率由 960.7 变为 360.3 MBit/s（HE NSS2→NSS1），吞吐由基线约 400 降至稳定平台 272 Mbps（-32%），恢复后回升，全程仅 1 次重传。A-MPDU 聚合参数无运行时调节入口，属关联期能力协商，需断开重连或 reload 生效，聚合长度由固件自动决策。软件队列 txq 参数（limit/memory_limit/quantum）实时可调且回读命中。三层最小调度粒度：软件队列为包/帧粒度（DRR quantum 字节粒度），固件为 MCU 命令与帧描述符粒度（EDCA 专属约 372μs），硬件为帧/PPDU 粒度（下一帧即生效）。')

    # ===== 2 测试环境与链路 =====
    add_h1(doc, '2 测试环境与链路')
    add_h2(doc, '2.1 硬件与系统')
    add_table(doc,
              ['项目', '值'],
              [['板型', 'BPI-R4（MT7988A，MT7996 WiFi 7 三频）'],
               ['固件', 'OpenWrt 24.10.0 r28427-6df0e3d02a'],
               ['内核', '6.6.73（补丁驱动 mt7996e 含 EDCA debugfs）'],
               ['管理网段', 'br-lan 192.168.1.1/24'],
               ['PC', 'Windows，WLAN3（MediaTek USB 网卡）192.168.1.126']],
              aligns=['left', 'left'], widths=[4, 9])
    add_h2(doc, '2.2 无线拓扑（方案 A）')
    add_table(doc,
              ['接口', '角色', 'SSID/参数', '说明'],
              [['phy0.1-ap0', '5G AP（被测下行）', 'BPI-R4-5G，ch149 HE80，psk2', '电脑直连，iperf3 反向打流（AP 下行）'],
               ['phy0.0', '2.4G AP', 'BPI-R4（2.4G）', '背景接口，本实验未打流'],
               ['station', '电脑 WLAN3', 'MAC 90:de:80:1c:6a:7a', 'iperf3 客户端（接收端）']],
              aligns=['left', 'left', 'left', 'left'], widths=[2.6, 3.2, 4, 6])
    add_h2(doc, '2.3 工具与入口')
    add_table(doc,
              ['工具', '位置', '作用'],
              [['edca_set.py', '板端 /root/', 'nl80211 SET_WIPHY+TXQ_PARAMS 实时下发 EDCA'],
               ['measure_edca.py', '板端 /root/', '下发时延定量测量（ns 计时，含基线模式）'],
               ['iw 6.9', '板端', 'set bitrates / set txq / station get 等实时入口'],
               ['iperf3', '板端 server(5201)+PC 客户端', '反向打流与打流态测量'],
               ['debugfs', '板端 /sys/kernel/debug/ieee80211/phy0/mt76/', 'edca 回读、tx_stats、xmit-queues、hw-queues']],
              aligns=['left', 'left', 'left'], widths=[3.5, 5, 6])

    # ===== 3 实验设计 =====
    add_h1(doc, '3 实验设计')
    add_h2(doc, '3.1 三类参数调节入口侦察')
    add_table(doc,
              ['参数', '候选入口', '侦察结果', '结论'],
              [['EDCA', 'nl80211 TXQ_PARAMS / debugfs edca', 'edca_set.py 写入→debugfs 回读命中', '有实时入口'],
               ['MCS', 'iw dev set bitrates', '支持 legacy/ht/vht/he 掩码，空参清掩码', '有实时入口'],
               ['A-MPDU', 'iw station set / station debugfs / mt76 debugfs', 'station set 仅 txpwr/airtime_weight/vlan；debugfs 无 ampdu_factor/density 节点', '无实时入口（关联期协商）'],
               ['软件队列', 'iw phy0 set txq', 'limit/memory_limit/quantum 均可写', '有实时入口']],
              aligns=['left', 'left', 'left', 'left'], widths=[2.6, 4.5, 6, 3])
    add_h2(doc, '3.2 实验矩阵')
    add_table(doc,
              ['实验', '内容', '状态'],
              [['1 A-MPDU 聚合参数实时调整', '入口侦察+聚合状态观察（agg_status/tx_stats）', '限制结论（无 runtime 入口）'],
               ['2 MCS 速率掩码实时调整', '打流中全层掩码锁定→回读→恢复，吞吐三段式', '完成（决定性证据）'],
               ['3 EDCA 下发时延定量', '基线（AC=-1）+ 打流态 100 次下发统计', '完成（median 463.5μs）'],
               ['4 软件队列 txq 实时调整', 'quantum 300→512→65535 回读命中', '完成']],
              aligns=['left', 'left', 'left'], widths=[4.5, 6, 4.5])

    # ===== 4 EDCA =====
    add_h1(doc, '4 EDCA 实时下发实测')
    add_h2(doc, '4.1 下发通路')
    add_body(doc, 'EDCA 实时下发链路为：用户态 edca_set.py 构造 nl80211 命令（SET_WIPHY + WIPHY_TXQ_PARAMS）→ cfg80211 → mac80211 conf_tx → mt76 驱动（mt7996_mcu_set_tx 构造 MCU 命令）→ 固件 MCU 更新 EDCA 参数表 → 硬件发送引擎按新参数调度。补丁 999-mt7996-edca-debugfs.patch 打通该通路并新增 debugfs 回读节点。')
    add_h2(doc, '4.2 生效即时性（120 秒打流切换）')
    add_body(doc, '5G 链路反向打流 120s，约 60s 处下发激进档 EDCA（BE 1/3/7/0）：全程 398 Mbps、25 次重传，写入瞬间吞吐由 36.5 短暂下坠至 167 Mbps 后立即恢复，无重连、无 AP 重启、报告无归零。判定：命令写入瞬间参数已生效，业务流量不中断，“免重载即时生效”成立。')
    add_h2(doc, '4.3 下发时延定量（5G 打流态）')
    add_body(doc, 'measure_edca.py phy0.1-ap0 0 1 3 7 0 100（打流态 100 次下发）与 AC=-1 基线（GETFAMILY 纯 netlink 往返 100 次）实测结果如下（单位 μs）。')
    add_table(doc,
              ['场景（各 100 次）', 'min', 'median', 'mean', 'p90', 'p99', 'max'],
              [['A 基线（GETFAMILY，AC=-1）', '88.7', '91.7', '93.1', '96.2', '115.9', '148.2'],
               ['B EDCA 5G 打流态下发', '249.0', '463.5', '491.4', '627.1', '1296.8', '1333.9'],
               ['C 专属耗时（B−A）', '—', '371.8', '398.3', '530.9', '1180.9', '1185.7']],
              aligns=['left', 'right', 'right', 'right', 'right', 'right', 'right'],
              widths=[5.6, 1.7, 1.7, 1.7, 1.7, 1.7, 1.7])
    add_body(doc, '基线分布极窄（88-148μs），说明 netlink 往返本身稳定；EDCA 打流态中位 463.5μs，扣除基线后专属耗时约 371.8μs，即驱动构造 MCU 命令 + 固件处理确认的耗时，与 mt76 固件命令交互（数百 μs 级）相符。尾部离群（>1ms）来自 CPU 调度与无线中断延迟，判读以 median/p90 为准。')
    add_h2(doc, '4.4 与 2.4G 历史数据对比')
    add_table(doc,
              ['口径（μs）', '2.4G（早前实测）', '5G（本次）'],
              [['基线 median', '94.4', '91.7'],
               ['空闲态 median', '215.5', '—'],
               ['打流态 median', '322.1', '463.5'],
               ['专属耗时（打流−基线）', '≈228', '371.8']],
              aligns=['left', 'right', 'right'], widths=[5, 4.5, 4.5])

    # ===== 5 MCS =====
    add_h1(doc, '5 MCS 速率掩码实时调整实测')
    add_h2(doc, '5.1 入口与命令形式')
    add_body(doc, '入口为 iw dev <ifname> set bitrates，支持 legacy-<2.4|5>、ht-mcs、vht-mcs、he-mcs 掩码，空参清除掩码（恢复自动）。实测发现：iw 6.9 的 station dump/get 必须写全 “iw dev <ifname> station …”，省略 dev 直接输出 usage；单独 vht-mcs 或 he-mcs 掩码约束不完整，需全层锁定（legacy+ht+vht+he 同时给出）才可靠生效。')
    add_h2(doc, '5.2 实时生效证据（station 速率跳变）')
    add_body(doc, '打流中执行全层锁定命令 iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0，station 回读显示下行速率由锁定前 960.7 MBit/s（HE-MCS9 NSS2）降为 360.3 MBit/s（HE-MCS7 NSS1），恢复命令（空参）后回升至 864.8 MBit/s（HE-MCS8 NSS2）。全程无重连（connected time 连续），命令实时作用于固件速率表。')
    add_h2(doc, '5.3 吞吐三段式')
    add_body(doc, '40s 反向打流中，锁定段（约 24-37s）吞吐稳定在 272 Mbps 平台（14 个连续 1s 报告 267-274 Mbps），较基线约 400 Mbps 下降 32%；恢复段（38-40s）回升至 356/424 Mbps。全程仅 1 次重传、tx bytes 连续增长，无断流。收敛时间：命令下发瞬时生效，速率控制（minstrel_ht）重收敛约 10s，该收敛属算法特性而非下发时延。')
    add_h2(doc, '5.4 关键结论')
    add_body(doc, 'MCS 速率掩码为“即时生效、免重载”：nl80211 下发后 station 速率字段与实测吞吐均在打流过程中实时响应，无需 reload WiFi；下行链路实际生效边界为下一个 iperf 报告周期（秒级），物理层收敛由 minstrel 自适应算法决定。')

    # ===== 6 A-MPDU =====
    add_h1(doc, '6 A-MPDU 聚合参数：限制结论')
    add_h2(doc, '6.1 运行时入口缺失证据')
    add_body(doc, '（1）iw station set 仅支持 txpwr/airtime_weight/vlan，无 ampdu 参数；（2）station debugfs（stations/90:de:80:1c:6a:7a/）仅有 agg_status/eht_capa/ht_capa/vht_capa/airtime/aqm/aql 等节点，无 ampdu_factor/ampdu_density；（3）mt76 debugfs 无聚合参数配置节点。聚合参数（A-MPDU factor/density）属 IEEE 802.11 关联期 ADDBA 能力协商，运行时无法通过 nl80211/debugfs 修改，只能断开重连或修改 hostapd 配置后 wifi reload 生效。')
    add_h2(doc, '6.2 聚合状态观察（打流中实测）')
    add_body(doc, '打流中读取聚合/队列统计：agg_status 显示 TID00（BE）与 TID03 聚合会话已建立（TX DTKN 0x22/0x23）；mt76 tx_stats 显示 5G 频段 A-MPDU 长度分布以单帧为主（Length=1 共 268877 次、2-10 帧 82653 次、长聚合稀少），A-MSDU 打包 7 个 MSDU 占 57%；Tx PER 11%、BA miss 25174。结论：聚合会话存在且聚合长度由驱动/固件自动决策，无运行时干预入口。')
    add_h2(doc, '6.3 可观察手段')
    add_body(doc, '聚合行为可通过 station agg_status、mt76 tx_stats（A-MPDU 长度分布）、hw-queues（PLE/PSE 硬件队列）与 xmit-queues（软件→硬件队列流转）观察。')

    # ===== 7 软件队列 =====
    add_h1(doc, '7 软件队列调度实测')
    add_h2(doc, '7.1 队列结构')
    add_body(doc, 'iw phy0 get txq 显示 mac80211 flow 队列：Packet limit 8192 pkts、Memory limit 16777216 bytes、Quantum 300 bytes、Number of queues 4096。mt76 xmit-queues 显示 MAIN0-2（数据）、MCUWM/MCUWA/MCUFWDL（固件命令）软件队列，hw-queued 字段反映入硬件队列的帧数。')
    add_h2(doc, '7.2 实时调整验证')
    add_body(doc, 'iw phy0 set txq quantum 512 与 quantum 65535 连续下发，iw phy0 get txq 回读精确命中（300→512→65535 bytes），无 reload。说明软件队列 DRR 参数（limit/memory_limit/quantum）为实时可调入口，作用于 mac80211 fq 调度器。')
    add_h2(doc, '7.3 硬件队列快照')
    add_body(doc, 'hw-queues 显示固件 PLE（packet link engine）与 PSE（packet switch engine）队列状态，可列出每个 station 的 wcid/AC 入队情况（如 STA 90:de:80:1c:6a:7a wcid 1 AC02），为硬件层调度观察点。')

    # ===== 8 三层调度粒度 =====
    add_h1(doc, '8 三层调度粒度分析')
    add_h2(doc, '8.1 软件队列层')
    add_body(doc, '实体为 mac80211 TXQ（fq 每流队列）+ mt76 xmit-queues，调度算法为 DRR（fq 以 quantum 字节为预算轮转各流队列）。最小调度粒度为包/帧粒度（每个 MPDU 一次出队决策），DRR 参数（quantum）为字节粒度可调（1~2^32）。实测 quantum 实时可调且回读命中，属于本层可实时干预的最小单位。')
    add_h2(doc, '8.2 固件层')
    add_body(doc, '实体为 MT7996 固件 MCU 与 PLE/PSE 队列。调度机制为 MCU 命令更新配置（EDCA 参数表、速率表）+ 帧描述符（TXD）入队。最小调度粒度为命令粒度（配置更新）与帧描述符粒度。实测 EDCA 专属耗时 371.8μs（驱动+固件 MCU 往返），MCS 速率表更新瞬时（station 速率字段立即变化），证明固件命令交互在数百 μs 级完成，属微秒级实时层。')
    add_h2(doc, '8.3 硬件层')
    add_body(doc, '实体为基带发送引擎（TX DMA + 无线前端）。调度机制为按固件已更新的 EDCA/速率表对已入队帧逐帧发送，A-MPDU 聚合长度由硬件自动决定（tx_stats 长度分布可证）。最小调度粒度为帧/PPDU 粒度（发送一个 PPDU 的决策），下一帧即用新参数，μs 级。')
    add_h2(doc, '8.4 最小调度粒度结论')
    add_table(doc,
              ['层', '实体/代码', '调度算法', '最小调度粒度', '实时入口', '实测实时性'],
              [['软件队列', 'mac80211 TXQ fq + mt76 xmit-queues', 'DRR（quantum 字节轮转）', '包/帧粒度；quantum 1~2^32 字节', 'iw phy0 set txq', '即时（回读命中）'],
               ['固件', 'MT7996 MCU + PLE/PSE', 'MCU 命令 + 帧描述符队列', '命令粒度；帧描述符粒度', 'nl80211→mt76 MCU（EDCA/速率）', 'EDCA 专属 371.8μs；速率瞬时'],
               ['硬件', '基带发送引擎', '按 EDCA/速率表逐帧发送', '帧/PPDU 粒度（聚合自动）', '由固件配置驱动', '下一帧生效（μs 级）']],
              aligns=['left', 'left', 'left', 'left', 'left', 'left'], widths=[2.2, 3.6, 3.2, 3.4, 3.2, 3.4])

    # ===== 9 结论矩阵 =====
    add_h1(doc, '9 结论矩阵')
    add_table(doc,
              ['参数', '命令入口', '即时生效', '需 reload', '实测时延/证据'],
              [['EDCA', 'nl80211 TXQ_PARAMS（edca_set.py）', '是', '否', '打流态 median 463.5μs、专属 371.8μs；120s 写入无断流'],
               ['MCS', 'iw dev set bitrates（全层锁）', '是', '否', 'station 960→360→865 MBit/s；吞吐 400→272→424 Mbps；收敛约 10s'],
               ['A-MPDU', '无运行时入口（关联期协商）', '否', '是（重连/reload）', 'agg_status 会话存在；tx_stats 长度分布由固件自动决策'],
               ['软件队列 txq', 'iw phy0 set txq', '是', '否', 'quantum 300→65535 回读命中']],
              aligns=['left', 'left', 'left', 'left', 'left'], widths=[2.6, 4.2, 1.8, 2.6, 6.8])

    # ===== 10 复现步骤 =====
    add_h1(doc, '10 复现步骤（命令清单）')
    add_h2(doc, '10.1 EDCA 时延定量')
    add_code(doc, 'python3 /root/measure_edca.py phy0.1-ap0 -1 1 3 7 0 100   # A 基线（AC=-1）')
    add_code(doc, 'iperf3.exe -c 192.168.1.1 -p 5201 -R -t 45 -i 1 --logfile iperf3_5g_latency.txt   # PC 打流')
    add_code(doc, 'python3 /root/measure_edca.py phy0.1-ap0 0 1 3 7 0 100    # B 打流态（打流 6s 后执行）')
    add_h2(doc, '10.2 MCS 实时切换')
    add_code(doc, 'iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0   # 全层锁')
    add_code(doc, 'iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a           # 回读（必须写全 dev）')
    add_code(doc, 'iw dev phy0.1-ap0 set bitrates                            # 空参恢复自动')
    add_h2(doc, '10.3 软件队列实时调整')
    add_code(doc, 'iw phy0 set txq quantum 512 && iw phy0 get txq            # 改后回读命中')
    add_h2(doc, '10.4 聚合状态观察')
    add_code(doc, 'cat /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/90:de:80:1c:6a:7a/agg_status')
    add_code(doc, 'cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats          # A-MPDU 长度分布')

    # ===== 11 局限与后续 =====
    add_h1(doc, '11 局限与后续')
    add_body(doc, '（1）EDCA 的“固件内部最后一步写硬件寄存器”无法从软件侧观测，增量在 μs 量级内，ACK 返回即视为参数处理完成边界；（2）MCS 收敛时间约 10s 属 minstrel_ht 算法特性，与命令下发时延无关，如需更快收敛需改速率控制算法本身；（3）A-MPDU 如需运行时调整，可行的路径是修改驱动/固件聚合阈值后编译部署 .ko（与 EDCA 补丁同模式），或改 hostapd 配置 reload；（4）软件队列 DRR 参数在单客户端单流场景无可观测差异，多客户端/多 AC 竞争场景才有调度意义，可作为后续多流实测方向。')

    doc.save(OUT)
    print('SAVED:', OUT)


if __name__ == '__main__':
    main()
