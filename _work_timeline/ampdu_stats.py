# -*- coding: utf-8 -*-
"""A-MPDU 实验三阶段统计（供报告引用）。"""
import re, sys, statistics as st

LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+([\d.]+)\s+([KM])Bytes\s+([\d.]+)\s+([KM])bits/sec')

def parse(path):
    pts = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            m = LINE_RE.search(raw)
            if not m:
                continue
            t1 = float(m.group(2)); v = float(m.group(5))
            if m.group(6) == 'K':
                v /= 1000.0
            pts.append((t1, v))
    return pts

def phase(pts, a, b):
    ys = [v for t, v in pts if a <= t < b]
    return {
        'n': len(ys), 'mean': round(st.mean(ys), 1), 'median': round(st.median(ys), 1),
        'min': round(min(ys), 1), 'max': round(max(ys), 1),
        'final_mean': round(st.mean([v for t, v in pts if t <= 1.01]), 1),
    }

pts = parse(sys.argv[1])
issue = float(sys.argv[2]) if len(sys.argv) > 2 else 45.179
restore = float(sys.argv[3]) if len(sys.argv) > 3 else 75.33

print('total samples:', len(pts))
print('issue=%.3f restore=%.2f' % (issue, restore))
for name, a, b in (('A 无限制', 0, issue), ('B 受限(cap=2)', issue + 1, restore), ('C 恢复无限制', restore + 1, 9999)):
    print('%s: %s' % (name, phase(pts, a, b)))

# 拐点：下发后首个低于前段中位数 60% 的点
before = [v for t, v in pts if t <= issue]
base = st.median(before)
onset = None
for t, v in pts:
    if t >= issue and v < base * 0.6:
        onset = t; break
print('base_median=%.1f  onset=%s  delta=%s' % (base, onset, round(onset - issue, 2) if onset else None))

# 恢复拐点：恢复后首个高于受限段中位数 1.5 倍的点
capped = [v for t, v in pts if issue + 1 <= t < restore]
cm = st.median(capped)
onset2 = None
for t, v in pts:
    if t >= restore and v > cm * 1.5:
        onset2 = t; break
print('capped_median=%.1f  restore_onset=%s  delta=%s' % (cm, onset2, round(onset2 - restore, 2) if onset2 else None))
