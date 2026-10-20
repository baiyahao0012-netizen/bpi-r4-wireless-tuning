# -*- coding: utf-8 -*-
"""EDCA 实时下发时序图绘制：iperf3 每秒吞吐 vs 下发时刻。

用法：
  python plot_edca_timeline.py --log <iperf3日志> [--issue-sec 59.3] [--out x.png]
                              [--title "..."] [--csv out.csv]

- 解析 iperf3 -i 1 的每秒行，得到 (时间, Mbps) 序列；
- 若给出 --issue-sec：画竖线标注"命令下发时刻"，并自动检测拐点标注"数据变化时刻"与 Δ；
- 未给出时按全局最小值位置推定下发时刻（仅用于预览）。
"""
import re, sys, json, argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

LINE_RE = re.compile(
    r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+([\d.]+)\s+([KM])Bytes\s+([\d.]+)\s+([KM])bits/sec')


def parse_iperf3(path):
    pts = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            m = LINE_RE.search(raw)
            if not m:
                continue
            t0, t1, xfer, xunit, bw, bunit = m.groups()
            t1 = float(t1)
            val = float(bw)
            if bunit == 'K':
                val /= 1000.0
            if xunit == 'K':
                pass  # 传输量单位不影响吞吐，忽略
            pts.append((t1, val))
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', required=True)
    ap.add_argument('--issue-sec', type=float, default=None,
                    help='命令下发时刻（相对打流开始的秒数）')
    ap.add_argument('--out', default='edca_timeline.png')
    ap.add_argument('--csv', default=None)
    ap.add_argument('--title', default='EDCA 实时下发时序图（iperf3 每秒吞吐 · 下行反向打流）')
    args = ap.parse_args()

    pts = parse_iperf3(args.log)
    if not pts:
        print('未从日志解析到任何每秒数据行：%s' % args.log)
        sys.exit(1)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    issue = args.issue_sec
    inferred = False
    if issue is None:
        imin = min(range(len(ys)), key=lambda i: ys[i])
        issue = xs[imin]
        inferred = True

    # 拐点：下发后第一个显著低于"下发前基线中位数一半"的采样
    before = [y for x, y in zip(xs, ys) if x <= issue]
    base = sorted(before)[len(before) // 2] if before else sorted(ys)[len(ys) // 2]
    onset = None
    for x, y in zip(xs, ys):
        if x >= issue and y < base * 0.6:
            onset = x
            break
    delta = (onset - issue) if onset else None

    if args.csv:
        with open(args.csv, 'w', encoding='utf-8-sig') as f:
            f.write('t_end_s,mbps\n')
            for x, y in pts:
                f.write('%.2f,%.1f\n' % (x, y))
        print('CSV: %s' % args.csv)

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)
    ax.plot(xs, ys, '-', color='#1f5fbf', lw=1.6, label='iperf3 每秒吞吐（下行）')
    ax.axvline(issue, color='#d62b2b', ls='--', lw=1.6,
               label=('命令下发时刻≈%.1fs（由吞吐拐点推定）' % issue) if inferred
                     else ('命令下发时刻 t=%.1fs' % issue))
    if onset is not None:
        ax.axvline(onset, color='#e08a00', ls=':', lw=1.6,
                   label='观测到吞吐变化 t=%.1fs（Δ≈%.1fs，受 1s 粒度限制）' % (onset, delta))
        ax.annotate('', xy=(onset, max(ys) * 0.82), xytext=(issue, max(ys) * 0.82),
                    arrowprops=dict(arrowstyle='<->', color='#555', lw=1.2))
    ax.set_xlabel('打流开始后时间 (s)')
    ax.set_ylabel('吞吐 (Mbit/s)')
    ax.set_title(args.title, fontsize=11)
    ax.grid(alpha=0.3)
    ax.set_ylim(0, max(ys) * 1.12)
    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout()
    fig.savefig(args.out)
    print('PNG: %s' % args.out)

    summary = {
        'log': args.log, 'n_samples': len(pts),
        'issue_sec': issue, 'issue_inferred': inferred,
        'base_median_mbps': round(base, 1),
        'change_onset_sec': onset, 'delta_sec': (round(delta, 2) if delta is not None else None),
        'min_mbps': min(ys), 'max_mbps': max(ys),
        'pre_mean_mbps': round(sum(before) / len(before), 1) if before else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
