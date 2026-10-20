# -*- coding: utf-8 -*-
"""聚合窗口 cap vs 稳态吞吐 —— 阶梯扫描（当前正确拓扑：WLAN 连 BPI-R4-5G）。
每档 dwell 10~15s，取该档末尾 4s 采样中位数作为稳态吞吐。"""
import subprocess, time, os, re, statistics as st, sys

BOARD = '192.168.1.1'
IPERF = r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
CAP = '/sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap'
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, '_sweep_final.txt')
LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+([\d.]+)\s+([KM])Bytes\s+([\d.]+)\s+([KM])bits/sec')

def ssh(cmd, t=20):
    r = subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=8',
                        'root@' + BOARD, cmd], capture_output=True, timeout=t)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')

ssh('dmesg -C; echo 0 > %s' % CAP)
print('[init] dmesg cleared, cap=0 (uncapped)')

if os.path.exists(LOG):
    os.remove(LOG)
p = subprocess.Popen([IPERF, '-c', BOARD, '-p', '5201', '-R', '-t', '65', '-i', '1',
                      '--logfile', LOG, '--forceflush'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('[iperf3] pid=%d (65s)' % p.pid)

# (下发时刻 s, cap, 标签)
plan = [(10, 8, 'cap=8'), (22, 4, 'cap=4'), (34, 2, 'cap=2'), (52, 0, '恢复(cap=0/256)')]
t0 = time.perf_counter()
events = []
for tt, cap, label in plan:
    while time.perf_counter() - t0 < tt:
        time.sleep(0.02)
    rc, o, e = ssh('echo %d > %s' % (cap, CAP))
    events.append((round(time.perf_counter() - t0, 2), cap, label, rc))
    print('[t=%.1fs] write cap=%d (%s) rc=%d' % (events[-1][0], cap, label, rc))
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

# 各档稳态窗口（时刻 s 之后 2s 起，到下一档下发前 1s）
bounds = [(0, 10, 'cap=256（未限制，默认）')]
for i, (tt, cap, label) in enumerate(plan):
    nxt = plan[i + 1][0] if i + 1 < len(plan) else 70
    bounds.append((tt, nxt, label))

print('%-26s %5s %8s %8s %8s %8s' % ('档位', 'n', '均值', '中位数', '最小', '最大'))
rows = []
for a, b, label in bounds:
    ys = [v for t, v in pts if a + 2 <= t < b - 0.5]
    if not ys:
        continue
    rows.append((label, len(ys), round(st.mean(ys), 1), round(st.median(ys), 1), round(min(ys), 1), round(max(ys), 1)))
    print('%-26s %5d %8.1f %8.1f %8.1f %8.1f' % rows[-1])

with open(os.path.join(HERE, '_sweep_final_summary.txt'), 'w', encoding='utf-8') as f:
    f.write('档位\tn\t均值\t中位数\t最小\t最大\n')
    for r in rows:
        f.write('%s\t%d\t%.1f\t%.1f\t%.1f\t%.1f\n' % r)
print('\nSUMMARY -> _sweep_final_summary.txt')
