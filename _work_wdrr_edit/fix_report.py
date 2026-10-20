# -*- coding: utf-8 -*-
"""修复：移除误插入到目录区的新元素，重新定位正文标题后正确插入 6.4/6.5。"""
import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

TARGET = r'D:\Desktop\AI 辅助对话\mac80211 WDRR 调度器部署验证报告.docx'
doc = Document(TARGET)

def para_text(p_el):
    return ''.join(p_el.itertext())

def find_heading(frag):
    """正文标题（Heading 样式），排除 TOC 行。"""
    for p in doc.paragraphs:
        if frag in p.text and p.style is not None and ('Heading' in p.style.name or '标题' in p.style.name):
            return p
    return None

def find_para(frag):
    for p in doc.paragraphs:
        if frag in p.text:
            return p
    return None

def set_p_text(p_el, text):
    rpr = None
    for r in p_el.iter(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        if rpr is not None:
            rpr = copy.deepcopy(rpr)
        break
    for r in p_el.findall(qn('w:r')):
        p_el.remove(r)
    r_new = OxmlElement('w:r')
    if rpr is not None:
        r_new.append(rpr)
    t = OxmlElement('w:t')
    t.text = text
    t.set(qn('xml:space'), 'preserve')
    r_new.append(t)
    p_el.append(r_new)

def new_p_like(src_p_el, text):
    el = copy.deepcopy(src_p_el)
    set_p_text(el, text)
    return el

def new_table_like(src_tbl_el, rows_vals):
    el = copy.deepcopy(src_tbl_el)
    trs = el.findall(qn('w:tr'))
    for ri, r in enumerate(trs[:len(rows_vals)]):
        tcs = r.findall(qn('w:tc'))
        for ci, c in enumerate(tcs[:len(rows_vals[ri])]):
            ps = c.findall(qn('w:p'))
            if ps:
                set_p_text(ps[0], rows_vals[ri][ci])
    return el

# ---- 1) 移除误插入到目录区的新元素 ----
body = doc.element.body
kids = list(body)
start = None
end = None
for el in kids:
    if el.tag == qn('w:p'):
        txt = para_text(el)
        if start is None and '6.4 WDRR 加权专项验证' in txt:
            start = el
        if '为排除 WDRR 版引入性能退化' in txt:
            end = el
removed = 0
if start is not None and end is not None:
    started = False
    for el in list(body):
        if el is start:
            started = True
        if started:
            body.remove(el)
            removed += 1
        if el is end:
            break
print('REMOVED_ELEMS', removed)

# ---- 2) 重新定位正确锚点 ----
h63 = find_heading('6.3 结果解读')
assert h63 is not None, '6.3 heading not found'
b63 = find_para('两次打流均验证')
assert b63 is not None, '6.3 body not found'
p7 = find_heading('环境与配置快照')
assert p7 is not None, 'sec7 heading not found'
cap61 = find_para('表 6-1 打流回归结果')
assert cap61 is not None, 'cap61 not found'

tbl61 = None
for t in doc.tables:
    head = ' '.join(c.text for c in t.rows[0].cells)
    if '平均吞吐' in head:
        tbl61 = t._tbl
        break
assert tbl61 is not None, 'table 6-1 not found'

# ---- 3) 确认 §5.3 / §6.3 已改写（此前已生效，此处仅校验） ----
p53 = find_para('执行 echo 2,1,1,1')
assert p53 is not None and 'sysfs 可写（参数可运行时调整' in p53.text, '5.3 rewrite missing'
assert 'per-AC 加权是否生效见 6.4' in b63.text, '6.3 rewrite missing'

# ---- 4) 正确插入 6.4 / 6.5 ----
rows62 = [
    ['权重', 'BE 流吞吐（Mbits/sec）', 'VO 流吞吐（Mbits/sec）', '比值（BE:VO）', '丢包'],
    ['1,1,1,1（基线）', '30.0', '29.4', '1.02:1', '0%'],
    ['4,1,1,1（加权）', '30.4', '30.0', '1.01:1', '0%'],
]
new_els = [
    new_p_like(h63._p, '6.4 WDRR 加权专项验证'),
    new_p_like(b63._p,
        '为验证 per-AC 权重是否真实改变调度比例，2026-10-19 补做双 AC 并发打流实验：'
        '板端 iperf3 同时向电脑端双 server 发起两个 UDP 全速流（-b 1000M），流 1 标记 DSCP 0（BE）、'
        '流 2 标记 DSCP 0x2e（EF，映射 AC_VO），各 30 秒；先以权重 1,1,1,1 跑基线，再改为 4,1,1,1'
        '（BE=4、VO=1）并重启 iperf3 客户端（新源端口 → 新 flow → 新权重）重跑。'),
    new_p_like(cap61._p, '表 6-2 WDRR 加权验证结果'),
    new_table_like(tbl61, rows62),
    new_p_like(b63._p,
        '两轮比值均为 1:1 量级（1.02:1 与 1.01:1），4:1 权重未产生任何调度比例变化；两轮丢包均为 0%，'
        '发送被调度器限速在链路容量内，分配比例完全由调度器决定。'),
    new_p_like(b63._p,
        '根因分析：mac80211 的 fq 为 per-txq（per-sta-per-tid）内部的 flow 公平调度器，AC 是 txq 的属性，'
        'AC 间竞争发生在 txq 层（airtime fairness / 驱动队列），fq 层 per-flow quantum 权重无法跨 AC 生效；'
        '同一 txq 内所有 flow 同 AC 同权重，权重相互抵消。结论：当前补丁在 fq 层实现 per-AC 权重，'
        '从架构上无法达成"按 AC 加权调度"目标，"运行时改参"仅证明 sysfs 可写；'
        '要实现 AC 加权，需将权重移至 txq 层调度（airtime 权重 / ieee80211_txq_schedule）。'),
    new_p_like(h63._p, '6.5 原版基线对照（.orig）'),
    new_p_like(b63._p,
        '为排除 WDRR 版引入性能退化，将板端驱动回滚至 .orig 原版（md5 d562be21358f4332600cae4164ee1bdd），'
        '同口径复测（板端单流 TCP 至电脑端 server，5G 链路，30 秒）：52.9 Mbits/sec、重传 0；'
        '对比 WDRR 版 53.3 Mbits/sec、重传 0，差异 0.4 Mbits/sec（0.8%），在测量噪声范围内，未发现性能退化。'),
]
anchor = p7._p
for el in new_els:
    anchor.addprevious(el)

# ---- 5) §7 表"上传副本"行更新 ----
for t in doc.tables:
    for r in t.rows:
        if '上传副本' in r.cells[0].text:
            r.cells[1].paragraphs[0].text = '/root/mac80211.wdrr.ko（持久副本）'
            break

doc.save(TARGET)
print('FIX_DONE')
