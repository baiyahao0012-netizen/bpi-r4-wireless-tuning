# -*- coding: utf-8 -*-
"""聚合窗口档位 vs 稳态吞吐 —— 交错设计（消除链路漂移）。
序列：unc → cap8 → unc → cap4 → unc → cap2 → unc，每档 10s；
每个受限档与相邻两个无限制档的中位数均值比较，抵消单调漂移。"""
import subprocess, time, os, re, statistics as st

BOARD = '192.168.1.1'
IPERF = r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
CAP = '/sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap'
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, '_sweep_il.txt')
LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+([\d.]+)\s+([KM])Bytes\s+([\d.]+)\s+([KM])bits/sec')

def ssh(cmd, t=20):
    r = subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=8',
                        'root@' + BOARD, cmd], capture_output=True, timeout=t)
    return r.returncode

ssh('dmesg -C; echo 0 > %s' % CAP)
print('[init] cap=0')

if os.path.exists(LOG):
    os.remove(LOG)
p = subprocess.Popen([IPERF, '-c', BOARD, '-p', '5201', '-R', '-t', '72', '-i', '1',
                      '--logfile', LOG, '--forceflush'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('[iperf3] pid=%d (72s)' % p.pid)

# (时刻, cap)  cap=0 表示恢复默认窗口 256
plan = [(10, 8), (20, 0), (30, 4), (40, 0), (50, 2), (60, 0)]
t0 = time.perf_counter()
for tt, cap in plan:
    while time.perf_counter() - t0 < tt:
        time.sleep(0.02)
    rc = ssh('echo %d > %s' % (cap, CAP))
    print('[t=%.1fs] cap=%d rc=%d' % (time.perf_counter() - t0, cap, rc))
p.wait()
print('[iperf3] done\n')

pts = []
for raw in open(LOG, errors='replace'):
    m = LINE_RE.search(raw)
    if m:
        v = float(m.group(5))
        if m.group(6) == 'K':
            v /= 1000.0
        pts.append((float(m.group(2)), v))

def med(a, b):
    ys = [v for t, v in pts if a <= t < b]
    return (round(st.median(ys), 1), len(ys)) if ys else (None, 0)

phases = [(0, 10, '无限制①'), (10, 20, 'cap=8'), (20, 30, '无限制②'),
          (30, 40, 'cap=4'), (40, 50, '无限制③'), (50, 60, 'cap=2'),
          (60, 72, '无限制④(恢复)')]
res = {}
for a, b, name in phases:
    m, n = med(a + 2, b)
    res[name] = m
    print('%-14s t=%d~%ds  n=%d  中位数=%s Mbit/s' % (name, a, b, n, m))

unc = [res['无限制①'], res['无限制②'], res['无限制③'], res['无限制④(恢复)']]
print('\n无限制档中位数：%s  (范围 %s~%s)' % (unc, min(unc), max(unc)))
print('\n%-10s %-16s %-16s %-10s' % ('档位', '相邻无限制基准', '受限中位数', '比值'))
lines = []
for cap_name, base_pair in (('cap=8', ('无限制①', '无限制②')), ('cap=4', ('无限制②', '无限制③')), ('cap=2', ('无限制③', '无限制④(恢复)'))):
    base = (res[base_pair[0]] + res[base_pair[1]]) / 2
    got = res[cap_name]
    ratio = round(got / base, 3)
    lines.append((cap_name, round(base, 1), got, ratio))
    print('%-10s %-16.1f %-16.1f %-10.3f' % (cap_name, base, got, ratio))

with open(os.path.join(HERE, '_sweep_il_summary.txt'), 'w', encoding='utf-8') as f:
    f.write('档位\t相邻无限制基准(Mbit/s)\t受限中位数(Mbit/s)\t比值\n')
    for r_ in lines:
        f.write('%s\t%.1f\t%.1f\t%.3f\n' % r_)
    f.write('\n各无限制档中位数: %s\n' % ', '.join(str(x) for x in unc))
print('\nSUMMARY -> _sweep_il_summary.txt')
