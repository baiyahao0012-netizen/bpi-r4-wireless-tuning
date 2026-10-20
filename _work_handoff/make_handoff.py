# -*- coding: utf-8 -*-
"""生成《调度器部署任务交接文档》Word（无模板创建，动态 TOC）。"""
import docx
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r'D:\Desktop\AI 辅助对话\调度器部署任务交接文档.docx'

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
    add_title(doc, '调度器部署任务交接文档')
    add_par(doc, '—— WDRR 补丁编译产物部署 · 当前卡点与接手指引', cn='宋体', size=12,
            align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_par(doc, '（BPI-R4 · OpenWrt 24.10.0 r28427 · 内核 6.6.73 · 2026-10-19）',
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

    # ===== 1 任务总览 =====
    add_h1(doc, '1 任务总览与一句话现状')
    add_h2(doc, '1.1 任务背景')
    add_body(doc, '本任务围绕 BPI-R4 开发板（MT7988A + MT7996 WiFi 7 三频）开展两阶段工作：第一阶段（已完成并验收）对无线参数实时下发能力（EDCA / MCS / A-MPDU / 软件队列）做系统性实测并产出报告；第二阶段（进行中）基于现有 DRR 调度代码修改实现私有 WDRR（加权 DRR）调度器，完成修改、编译、烧录、运行验证的完整链路。')
    add_h2(doc, '1.2 一句话现状')
    add_body(doc, 'WDRR 补丁已成功应用到 backports-6.12.6 两个 variant，mac80211.ko 编译成功且符号/字符串验证确认补丁在内，产物已从 WSL 拷入 Windows；当前唯一卡点是“电脑到板子的 SSH（22 端口）连不上”，部署（烧录）无法进行。卡点根因已从“板端服务异常”缩小到“5G 无线链路不稳定”：期间已修复一个明确的板端问题（重启后国家码未设置导致 5G 频段被禁、SSID 消失），链路恢复后 SSH 仍时断时续，最近一轮连续 10 次 TCP 探测 22 端口全部失败。')

    # ===== 2 现有资产 =====
    add_h1(doc, '2 我现在有的东西（资产清单）')
    add_h2(doc, '2.1 硬件与系统')
    add_table(doc,
              ['项目', '值'],
              [['目标板', 'BPI-R4（MT7988A SoC，MT7996 WiFi 7 三频）'],
               ['固件', 'OpenWrt 24.10.0 r28427-6df0e3d02a'],
               ['内核', '6.6.73'],
               ['管理网段', 'br-lan 192.168.1.1/24；root 空密码 SSH（22）'],
               ['电脑', 'Windows；WLAN3（MediaTek USB 网卡）192.168.1.126 连板子 5G；WLAN（Realtek 8852CE）192.168.3.46 连外网 DianGroup103']],
              aligns=['left', 'left'], widths=[4, 12])
    add_h2(doc, '2.2 编译产物与脚本（D:\\Desktop\\AI 辅助对话\\_build\\）')
    add_table(doc,
              ['文件', '说明'],
              [['mac80211.ko', 'WDRR 版驱动产物，6603848 字节，md5 49f2aca91f3228adcd83b205f5338d61；WSL 源路径 .pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko'],
               ['apply_wdrr.py', '补丁应用脚本（单行锚点版，regular+smallbuffers 双树可跑）'],
               ['build10.sh', '编译主脚本（clean→prepare→双树 apply→verify→compile -j24→locate→nm 校验），WSL /root/build10.sh'],
               ['build7.sh / build8.sh / build9.sh / verify8.sh / verify9.sh / txview.sh / fqview*.sh', '迭代过程脚本（历史）'],
               ['deploy_copy.sh', 'ko 从 WSL 拷 Windows 的脚本（已执行成功）'],
               ['001-wdrr.patch', '早期 patch 文件（因空行 malformed 未用，以 apply_wdrr.py 为准）']],
              aligns=['left', 'left'], widths=[6, 10])
    add_h2(doc, '2.3 报告与数据')
    add_table(doc,
              ['项目', '位置', '状态'],
              [['《无线参数实时下发系统性实测报告.docx》', 'D:\\Desktop\\kaggle\\EDCA恢复材料\\', '9页/11章，audit 0 错误，渲染逐页核对，已验收；按用户要求“全部完成后统一交付”，尚未交付'],
               ['报告渲染验收图', 'D:\\Desktop\\AI 辅助对话\\_work_systematic\\render_out\\render-rtvhs56m\\page-0001..0009.png', '逐页验收用'],
               ['iperf3 实测源数据', 'C:\\Users\\15732\\Desktop\\iperf3_5g_*.txt', '基线 376M / EDCA 切换 120s / latency / MCS 三段式 / agg 等'],
               ['2.4G EDCA 报告、EDCA恢复指南.md、edca_set.py、measure_edca.py、999-mt7996-edca-debugfs.patch', 'D:\\Desktop\\kaggle\\EDCA恢复材料\\', '原任务工具与材料']],
              aligns=['left', 'left', 'left'], widths=[5.5, 6.5, 4])
    add_h2(doc, '2.4 板端与电脑工具')
    add_table(doc,
              ['工具', '位置', '说明'],
              [['ssh_run.py / ssh_put.py', 'D:\\Desktop\\AI 辅助对话\\', 'SSH 执行器（root 空密码、3 次重试）'],
               ['edca_set.py / measure_edca.py', '板端 /root/', 'EDCA 实时下发与时延测量'],
               ['iperf3', '板端 server(5201) + 电脑 client', '打流测试'],
               ['debugfs', '板端 /sys/kernel/debug/ieee80211/phy0/mt76/', 'edca 回读、tx_stats、xmit-queues、hw-queues']],
              aligns=['left', 'left', 'left'], widths=[4.5, 6.5, 5])

    # ===== 3 干的事情 =====
    add_h1(doc, '3 干的事情（已完成工作）')
    add_h2(doc, '3.1 原任务：无线参数实时下发系统性实测（已完成验收）')
    add_body(doc, '在 BPI-R4 上完成四类实测并汇成 9 页报告：EDCA 打流态下发中位时延 463.5μs（扣除基线 91.7μs 后驱动+固件专属 371.8μs），即时生效免重载；MCS 全层速率掩码锁定后 station 速率 960.7→360.3→864.8 MBit/s、吞吐 400→272→424 Mbps，即时生效；A-MPDU 无运行时入口（关联期协商，限制结论）；软件队列 txq 参数（quantum 300→512→65535）实时可调回读命中。三层最小调度粒度：软件队列包/帧粒度、固件命令/帧描述符粒度（EDCA 专属约 372μs）、硬件帧/PPDU 粒度。')
    add_h2(doc, '3.2 新任务：WDRR 调度器修改与编译（已 100% 打通）')
    add_body(doc, '基于 mac80211 fq（DRR）实现 per-AC 加权 DRR，共 5 处修改：（1）include/net/fq.h 的 struct fq_flow 增加 int quantum 字段；（2）include/net/fq_impl.h 的 fq_tin_dequeue 出队轮转改为 flow->deficit += flow->quantum ? flow->quantum : fq->quantum；（3）fq_flow_init 将 flow->quantum 初始化为 0；（4）net/mac80211/tx.c 新增模块参数 static int fq_weight[IEEE80211_NUM_ACS]={1,1,1,1} 与 module_param_array(fq_weight,int,NULL,0644)；（5）fq_tin_dequeue_func 内首次出队时按 AC 权重初始化 flow->quantum = fq->quantum * fq_weight[ac]，并 printk_once 输出 WDRR 标记字符串。')
    add_body(doc, '编译链路：WSL 内 /root/build10.sh 全流程（clean→prepare→双树 apply→4 处 grep 验证→compile -j24→find ko→nm/strings 校验）跑通，COMPILE_RC=0，耗时约 125-136s。产物核验：nm 查到 __param_fq_weight 等 4 个符号，strings 查到 “private WDRR scheduler active (fq_weight=%d,%d,%d,%d)” 字符串，确认补丁已进产物。')
    add_body(doc, '编译环境取舍：曾按用户要求“两手准备（WSL+VM 并行）”，实测 VM 网络约 14kB/s、SDK 下载 0 字节，判定 VM 通道不可用后放弃，集中 WSL 编译（走宿主代理 172.25.112.1:7897）。')
    add_h2(doc, '3.3 部署尝试与故障诊断（进行中）')
    add_body(doc, '产物已拷到 D:\\Desktop\\AI 辅助对话\\_build\\mac80211.ko，原定通过 scp 上传板子 /tmp/ 后覆盖安装。但电脑到板子的 SSH 从“connect timeout”演变为“banner exchange: Connection refused”，期间进行了完整的板端/电脑端双侧诊断（详见第 5 章），并修复了重启后 5G AP 消失的问题。部署本身尚未开始。')

    # ===== 4 要做什么 =====
    add_h1(doc, '4 要做什么（目标与部署验证步骤）')
    add_h2(doc, '4.1 总目标')
    add_body(doc, '把 WDRR 版 mac80211.ko 烧录到板子并完成运行验证，证明私有调度器修改链路（修改→编译→烧录→运行验证）全通；全部完成后生成调度器部署报告，与原《无线参数实时下发系统性实测报告》统一交付。')
    add_h2(doc, '4.2 部署步骤（SSH 恢复后执行）')
    add_code(doc, 'scp "D:\\Desktop\\AI 辅助对话\\_build\\mac80211.ko" root@192.168.1.1:/tmp/')
    add_code(doc, '# 板端：确认驱动路径并备份、覆盖')
    add_code(doc, 'find /lib/modules/6.6.73 -name mac80211.ko')
    add_code(doc, 'cp /lib/modules/6.6.73/<实际路径>/mac80211.ko /lib/modules/6.6.73/<实际路径>/mac80211.ko.orig')
    add_code(doc, 'cp /tmp/mac80211.ko /lib/modules/6.6.73/<实际路径>/mac80211.ko && sync && reboot')
    add_h2(doc, '4.3 运行验证（重启后）')
    add_code(doc, 'cat /sys/module/mac80211/parameters/fq_weight        # 预期 "1,1,1,1"')
    add_code(doc, 'echo 2,1,1,1 > /sys/module/mac80211/parameters/fq_weight && cat /sys/module/mac80211/parameters/fq_weight')
    add_code(doc, 'dmesg | grep -i WDRR                                  # 预期 printk_once 标记字符串')
    add_body(doc, '打流回归：电脑 iperf3 反向打流（iperf3.exe -c 192.168.1.1 -p 5201 -R -t 40 -i 1 --logfile iperf3_wdrr.txt），对比部署前基线；多客户端/多 AC 场景可进一步观察 fq_weight 加权的调度差异。验证通过后按 word skill 流程生成部署报告，并与原报告统一 present_files 交付。')

    # ===== 5 目前什么情况 =====
    add_h1(doc, '5 目前什么情况（当前状态与诊断链）')
    add_h2(doc, '5.1 卡点')
    add_body(doc, '电脑到板子 192.168.1.1 的 SSH（22 端口）不可达。最近一轮连续 10 次 Test-NetConnection 22 端口全部失败；同时 5201 端口失败、80 端口偶通、ping 1-8ms 时通时慢。')
    add_h2(doc, '5.2 诊断时间线')
    add_table(doc,
              ['时间', '现象', '结论'],
              [['05:44', 'SSH 正常（Auth succeeded with blank password）', '链路与服务当时正常'],
               ['07:48', 'scp 卡认证 5 分钟（Timeout before auth）', 'TCP 可建但认证未完成'],
               ['07:48-08:30', 'ssh/scp 报 connect timeout 与 banner exchange refused 交替', 'TCP 到 22 时通时不通'],
               ['08:30 前后', 'ping 100% 丢失，80/5201/22 全不通，电脑搜不到 BPI-R4-5G', '无线链路整体断，5G AP 消失'],
               ['08:30 后', '串口查 logread：重启后 country 未设置（country 00），ch149 被判 PASSIVE-SCAN 不支持，hostapd 启动失败', '根因 1：5G AP 未起来（已修复）'],
               ['修复后', 'uci set wireless.radio1.country=CN + radio0 + commit + wifi reload；iwinfo 显示 BPI-R4-5G ch149 HE80 中心 155、Tx-Power 7dBm', '5G AP 恢复正常（已确认）'],
               ['当前', 'WLAN3 已连 BPI-R4-5G（信号 84% RSSI -42、1201 Mbps）；ping 1-8ms；22/5201 不通、80 偶通；10 次 22 重试全失败', '根因 2：无线链路下行丢包/不稳定（待解决）']],
              aligns=['left', 'left', 'left'], widths=[2.4, 7.6, 6])
    add_h2(doc, '5.3 已排除的项（无需重查）')
    add_body(doc, '（1）板端 dropbear 正常：板内 echo | nc 127.0.0.1 22 稳定返回 SSH-2.0-dropbear，重启后全新进程正常监听 0.0.0.0:22 与 :::22；（2）电脑出站 22 正常：Test-NetConnection github.com -Port 22 成功（走外网网卡）；（3）板端无 iptables 命令（-ash: iptables: not found），不存在 iptables 规则拦截；（4）dropbear 配置正常（/etc/config/dropbear：Port 22、PasswordAuth on、RootPasswordAuth on）；（5）TCP 数据面本身正常：此前 80/5201 曾稳定连通。')
    add_h2(doc, '5.4 当前结论（推断标注）')
    add_body(doc, '诊断指向无线链路（电脑 MT7921 USB 网卡 ↔ 板子 MT7996 5G AP）下行方向丢包：station dump 曾显示 tx failed 807 / tx retries 800（约 14.6% 失败率），ping 时延由 1ms 波动到 3-8ms，TCP 交互流（SSH）对丢包最敏感故最先失败，大流量端口（80/5201）时通时不通。链路恢复后 SSH 仍未稳定，与链路抖动一致。此结论为基于可观测数据的推断，最终定位需在链路侧抓包或换通道验证。')
    add_h2(doc, '5.5 建议的下一步（按优先级）')
    add_body(doc, '（1）换 2.4G 通道测 SSH：板端 2.4G AP（SSID BPI-R4，phy0.0-ap0）始终在线且 station 早期在 2.4G 上认证过；电脑 WLAN3 改连 BPI-R4，测 ping 与 ssh_run.py，若通则先完成部署；（2）换网卡：断开 WLAN3，用 Realtek WLAN（现连外网 DianGroup103）连 BPI-R4-5G 测 SSH（会短暂断外网，需代理后恢复）；（3）检查 USB 网卡：重新插拔 WLAN3、换 USB 口（USB 网卡供电不足/过热是 5G 掉链常见原因）；（4）串口复查链路：iwinfo phy0.1-ap0 info、iw dev phy0.1-ap0 station dump 再抓一次 tx failed 是否持续增长；（5）板端若有 tcpdump 则抓 22 流量定位丢包方向（OpenWrt 默认可能未装）；（6）链路稳定后按第 4 章部署。')

    # ===== 6 环境速查 =====
    add_h1(doc, '6 环境速查表（给接手者）')
    add_h2(doc, '6.1 板端无线与服务')
    add_table(doc,
              ['接口', 'SSID / 参数', '说明'],
              [['phy0.1-ap0', 'BPI-R4-5G，ch149 HE80，WPA2-PSK（psk2 12345678），addr 36:19:86:e0:2e:0f', '被测 5G AP（country 已设 CN）'],
               ['phy0.0-ap0', 'BPI-R4（2.4G），ch6', '备用通道'],
               ['phy0.2-ap0', 'BPI-R4-6G', '6G AP'],
               ['dropbear', '22（IPv4+IPv6）', 'root 空密码'],
               ['uhttpd', '80/443', 'LuCI 管理页'],
               ['dnsmasq', '53', 'DHCP 192.168.1.126 分配'],
               ['iperf3', '5201', '打流 server']],
              aligns=['left', 'left', 'left'], widths=[3, 8, 5])
    add_h2(doc, '6.2 WSL 编译链（关键路径）')
    add_table(doc,
              ['项目', '值'],
              [['SDK 根', '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64'],
               ['backports 双树', '$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-{regular,smallbuffers}/backports-6.12.6/'],
               ['关键文件', 'include/net/fq.h、include/net/fq_impl.h、net/mac80211/tx.c（fq_tin_dequeue_func 1385 行附近）'],
               ['编译脚本', '/root/build10.sh、/root/apply_wdrr.py'],
               ['代理', 'export http_proxy=http://172.25.112.1:7897 https_proxy=...'],
               ['板端实际用 variant', 'mac80211-regular']],
              aligns=['left', 'left'], widths=[3.5, 12.5])
    add_h2(doc, '6.3 验证口径与已知坑')
    add_table(doc,
              ['项目', '内容'],
              [['补丁核验', '源码 3 处 grep：fq_impl.h “flow->quantum ? flow->quantum”、fq.h “int quantum;”、tx.c “fq_weight[IEEE80211_NUM_ACS]”与“flow->quantum = fq->quantum * w”'],
               ['产物核验', 'nm 查 fq_weight 4 符号（__param_arr/_param/_param_str/__UNIQUE_ID）+ strings 查 “private WDRR scheduler active”'],
               ['坑：OpenWrt 编译缓存', '直接改 build_dir 源码后 make 会缓存命中（0.39s），必须 make package/kernel/mac80211/clean 后重编；compile 后源码树被清理，须 clean+prepare 先行再打补丁'],
               ['坑：板端无 iptables', '-ash: iptables: not found'],
               ['坑：logread -f 占终端', '会阻塞串口后续输入，用 Ctrl+C（0x03）终止，不影响系统'],
               ['坑：wsl.exe 传参', 'PowerShell 传参遇空格中文路径必拆坏，跨侧传文件用 base64 双写'],
               ['弃用', 'VM 通道（网络 ~14kB/s 下载 0 字节）；001-wdrr.patch 标准 patch 因空行 malformed（用 apply_wdrr.py）']],
              aligns=['left', 'left'], widths=[4.5, 11.5])
    add_h2(doc, '6.4 报告与工具位置')
    add_table(doc,
              ['项目', '路径'],
              [['原报告', 'D:\\Desktop\\kaggle\\EDCA恢复材料\\无线参数实时下发系统性实测报告.docx（sha256 e5dcc76c05a9a45c640fbd8347eb80580ca8666673f7c0b688a2eda7ba6b2bb4）'],
               ['报告生成工作区', 'D:\\Desktop\\AI 辅助对话\\_work_systematic\\（make_doc2.py / outline.md / render_out）'],
               ['SSH 工具', 'D:\\Desktop\\AI 辅助对话\\ssh_run.py / ssh_put.py'],
               ['板端脚本', '/root/edca_set.py、/root/measure_edca.py；补丁 999-mt7996-edca-debugfs.patch 在 EDCA恢复材料 目录'],
               ['iperf 日志', 'C:\\Users\\15732\\Desktop\\iperf3_5g_*.txt']],
              aligns=['left', 'left'], widths=[3.5, 12.5])

    # ===== 7 注意事项 =====
    add_h1(doc, '7 注意事项与协作约定')
    add_body(doc, '（1）用户偏好中文回复、结果导向、定量可复核；板端与编译操作由用户手动执行，需给出可直接粘贴的命令；（2）板子 root 无密码 SSH，登录直接回车；（3）报告类产物已验收的按“全部完成后统一交付”约定，不要提前交付；（4）本交接文档数据均来自实测命令输出；第 5.4 节结论为推断，接手者应以链路侧抓包或换通道实测复核；（5）最终部署报告生成前需重新读取 word skill 的 SKILL.md（RECALL 约定）。')

    doc.save(OUT)
    print('SAVED:', OUT)


if __name__ == '__main__':
    main()
