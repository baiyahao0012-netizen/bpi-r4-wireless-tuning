# -*- coding: utf-8 -*-
"""增量编辑部署报告：修正 §5.3/§6.3 措辞、新增 6.4 加权验证 + 6.5 原版基线、更新 §7 副本路径。"""
import copy
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

TARGET = r'D:\Desktop\AI 辅助对话\mac80211 WDRR 调度器部署验证报告.docx'
doc = Document(TARGET)

def find_para(frag):
    for p in doc.paragraphs:
        if frag in p.text:
            return p
    return None

def set_p_text(p_el, text):
    """清空 w:p 内所有 run，保留首个 run 的 rPr，写入新文本。"""
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

# ---- 1) §5.3 正文改写 ----
p53 = find_para('执行 echo 2,1,1,1')
assert p53 is not None, '5.3 para not found'
set_p_text(p53._p,
    '执行 echo 2,1,1,1 > /sys/module/mac80211/parameters/fq_weight 后回读，输出 2,1,1,1，'
    'sysfs 可写（参数可运行时调整，无需重编译）。需注意：flow->quantum 在首包出队时一次性写入（见 2.1），'
    '改写权重仅对之后新建的 flow 生效、对已存在 flow 无效；且按 6.4 架构分析，per-AC 权重置于 fq 层'
    '无法改变 AC 间调度比例。')

# ---- 2) §6.3 正文改写（去掉"参数生效"表述）----
p63 = find_para('两次打流均验证')
assert p63 is not None, '6.3 para not found'
set_p_text(p63._p,
    '两次打流均验证 WDRR 版驱动在持续流量下工作正常：不崩溃、不丢流、运行稳定'
    '（per-AC 加权是否生效见 6.4）。53.6 Mbps 为默认 MCS、单流（iperf3 -R）下的水平，'
    '与原报告在 5G 链路上经 EDCA/MCS 专项调优后的高吞吐（MCS 三段式 960.7、360.3、864.8 MBit/s，'
    'EDCA 时延 463.5 微秒即时生效）属不同测试口径，不可直接对比；测试环境存在多个邻居 5G AP 干扰，'
    '链路质量亦为影响因素。本次回归目标为调度器功能与稳定性验证，已全部达成。')

# ---- 3) 新增 6.4 / 6.5，插在 §7 标题前 ----
p7 = find_para('环境与配置快照')
assert p7 is not None, 'section 7 heading not found'
anchor = p7._p

# 样式基准：6.3 标题段、6.3 正文段、表 6-1 题注段、表 6-1 表格
h63 = find_para('6.3 结果解读')._p
b63 = p63._p
cap61 = find_para('表 6-1 打流回归结果')._p
tbl61 = None
for t in doc.tables:
    tt = ' '.join(c.text for row in t.rows for c in row.cells)
    if '2.4G' in tt and '10.2' in tt:
        tbl61 = t._tbl
        break
assert tbl61 is not None, 'table 6-1 not found'

# 表 6-2 数据
rows62 = [
    ['权重', 'BE 流吞吐（Mbits/sec）', 'VO 流吞吐（Mbits/sec）', '比值（BE:VO）', '丢包'],
    ['1,1,1,1（基线）', '30.0', '29.4', '1.02:1', '0%'],
    ['4,1,1,1（加权）', '30.4', '30.0', '1.01:1', '0%'],
]

new_els = [
    new_p_like(h63, '6.4 WDRR 加权专项验证'),
    new_p_like(b63,
        '为验证 per-AC 权重是否真实改变调度比例，2026-10-19 补做双 AC 并发打流实验：'
        '板端 iperf3 同时向电脑端双 server 发起两个 UDP 全速流（-b 1000M），流 1 标记 DSCP 0（BE）、'
        '流 2 标记 DSCP 0x2e（EF，映射 AC_VO），各 30 秒；先以权重 1,1,1,1 跑基线，再改为 4,1,1,1'
        '（BE=4、VO=1）并重启 iperf3 客户端（新源端口 → 新 flow → 新权重）重跑。'),
    new_p_like(cap61, '表 6-2 WDRR 加权验证结果'),
    new_table_like(tbl61, rows62),
    new_p_like(b63,
        '两轮比值均为 1:1 量级（1.02:1 与 1.01:1），4:1 权重未产生任何调度比例变化；两轮丢包均为 0%，'
        '发送被调度器限速在链路容量内，分配比例完全由调度器决定。'),
    new_p_like(b63,
        '根因分析：mac80211 的 fq 为 per-txq（per-sta-per-tid）内部的 flow 公平调度器，AC 是 txq 的属性，'
        'AC 间竞争发生在 txq 层（airtime fairness / 驱动队列），fq 层 per-flow quantum 权重无法跨 AC 生效；'
        '同一 txq 内所有 flow 同 AC 同权重，权重相互抵消。结论：当前补丁在 fq 层实现 per-AC 权重，'
        '从架构上无法达成"按 AC 加权调度"目标，"运行时改参"仅证明 sysfs 可写；'
        '要实现 AC 加权，需将权重移至 txq 层调度（airtime 权重 / ieee80211_txq_schedule）。'),
    new_p_like(h63, '6.5 原版基线对照（.orig）'),
    new_p_like(b63,
        '为排除 WDRR 版引入性能退化，将板端驱动回滚至 .orig 原版（md5 d562be21358f4332600cae4164ee1bdd），'
        '同口径复测（板端单流 TCP 至电脑端 server，5G 链路，30 秒）：52.9 Mbits/sec、重传 0；'
        '对比 WDRR 版 53.3 Mbits/sec、重传 0，差异 0.4 Mbits/sec（0.8%），在测量噪声范围内，未发现性能退化。'),
]
for el in new_els:
    anchor.addprevious(el)

# ---- 4) §7 表"上传副本"行更新 ----
for t in doc.tables:
    for r in t.rows:
        if '上传副本' in r.cells[0].text:
            r.cells[1].paragraphs[0].text = '/root/mac80211.wdrr.ko（持久副本）'
            break

doc.save(TARGET)
print('EDIT_DONE')
