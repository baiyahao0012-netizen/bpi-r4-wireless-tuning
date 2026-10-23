# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn

path = r'_work_final/BPI-R4_EDCA_AMPDU_MCS_WDRR_实测报告.docx'
doc = Document(path)

def cnfont(run, size=10.5, bold=False, color=None):
    run.font.name = 'Microsoft YaHei'
    run.font.size = Pt(size)
    run.bold = bold
    if color: run.font.color.rgb = color
    r = run._element
    r.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

def h(text):
    p = doc.add_heading(level=1)
    r = p.add_run(text); cnfont(r, 16, True, RGBColor(0x1F,0x3B,0x57))

def para(text):
    p = doc.add_paragraph(); r = p.add_run(text); cnfont(r, 10.5)
    p.paragraph_format.space_after = Pt(4)

h('十一、补充：混合 AC 竞争实验（VO vs BK）')
para('目的：不只测“命令多久到固件”，而是让两条真实 UDP 下行流分别落在 AC_VO 和 AC_BK，在参数改变时观察空口仲裁结果的变化，定量测出“业务可见的生效时间”。')
para('关键点：mac80211 的 ieee80211_select_queue() 会用 cfg80211_classify8021d() 覆盖 skb->priority，普通 SO_PRIORITY=6/2 会被重新分类成 BE。该函数对 256–263 有特殊处理，直接取 priority-256 作为 802.1d 优先级；因此 VO 用 SO_PRIORITY=262，BK 用 257，才能真正落到 AC_VO/AC_BK。')
para('方法：板端用 AF_PACKET 直接注入以太网帧（绕过 bridge 的 IP 分类），两个 UDP 流目的端口 6001/6002；PC 的 WLAN 5（Realtek 8812BU）接收，按 100 ms 分桶统计两路吞吐。20 s 内分三段：0–6 s 默认 EDCA；6–12 s VO 激进、BK 保守；12–20 s VO 保守、BK 激进。')

rows = [
    ('0–6 s 默认', '88.3 Mbit/s', '2.4 Mbit/s', '36.2 : 1'),
    ('6–12 s VO 激进（1/1/3/94）', '96.9 Mbit/s', '2.4 Mbit/s', '40.8 : 1'),
    ('12–20 s BK 激进（1/1/3/94）', '2.0 Mbit/s', '218.2 Mbit/s', '1 : 109'),
]
t = doc.add_table(rows=1, cols=4); t.style = 'Table Grid'
for i, x in enumerate(['阶段', 'VO 平均', 'BK 平均', 'VO:BK']):
    c = t.rows[0].cells[i]; c.text = ''
    r = c.paragraphs[0].add_run(x); cnfont(r, 9.5, True)
for row in rows:
    cells = t.add_row().cells
    for i, x in enumerate(row):
        cells[i].text = ''
        r = cells[i].paragraphs[0].add_run(x); cnfont(r, 9.5)

para('12 s 处切换的 100 ms 分桶：12.0–12.1 s 仍为 VO 113.4/BK 0.2；12.1–12.2 s 变为 VO 46.7/BK 94.6；12.2–12.3 s 为 VO 0/BK 175.8；12.3–12.4 s 进入新稳态 VO 0/BK 244.3。也就是说，业务可见变化在 0.1–0.2 s 内出现，0.2–0.3 s 进入新稳态。')
para('结论：只有 EDCA 参数改变、两条流发送逻辑完全相同的情况下，VO:BK 从 36:1 翻转到 1:109，证明参数确实改变了空口仲裁结果；同一次切换的命令→固件 ACK 为 0.24–0.98 ms（p50 约 0.25–0.34 ms）。因此 EDCA 的“生效”分为两层：命令/固件 0.2–1 ms，业务仲裁结果 0.1–0.3 s。')

doc.add_picture(r'_work_final/ac_mix_timeline.png', width=Cm(16.5))
doc.add_paragraph()
para('说明：默认 VO 已把 BK 压到约 2.4 Mbit/s，所以 6–12 s 再把 VO 调激进，VO 仅从 88.3 提到 96.9（+10%），因为 BK 已接近饿死；真正的因果翻转在 12 s 的 VO↔BK 参数对调。本实验只用一个接收 STA，目的是隔离 AC 仲裁；多 STA 场景会叠加 airtime fairness 影响。')

doc.save(path)
print('saved', path)
