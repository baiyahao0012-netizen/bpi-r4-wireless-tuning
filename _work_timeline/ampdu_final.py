# -*- coding: utf-8 -*-
"""A-MPDU 聚合窗口实时下发 —— 最终时序验证实验（PC 端编排）。

链路：mt7996 per-station debugfs 节点 agg_win_cap；写入时直接向固件重放
STA_REC_BA TLV（enable=false→true），把 TX BA winsize 实时改为上限值。

本实验同时采集两类证据：
  1) iperf3 下行每秒吞吐时序（下发时刻竖线 + 拐点 Δ）；
  2) 固件侧 A-MPDU 聚合长度分桶统计（tx_stats 的 Length/Count）：
     无限制区间窗口 vs 受限区间窗口各取两次快照，做差得到该区间的聚合长度分布，
     窗口缩小后分布应整体左移（大聚合桶计数下降）。

用法：
  python ampdu_final.py --cap 2 --issue-sec 50 --duration 125 --out-prefix ampdu_final
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT = os.path.join(HERE, 'plot_edca_timeline.py')
DEFAULT_IPERF3 = r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+([\d.]+)\s+([KM])Bytes\s+([\d.]+)\s+([KM])bits/sec')
CAPBOUNDS = [1, 10, 19, 28, 37, 46, 55, 79, 103, 127, 151, 175, 199, 223, 247]
CAPLABELS = ['1', '2-10', '11-19', '20-28', '29-37', '38-46', '47-55', '56-79',
             '80-103', '104-127', '128-151', '152-175', '176-199', '200-223', '224-247']


def ssh_cmd(board, cmd, timeout=30):
    argv = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
            'root@%s' % board, cmd]
    r = subprocess.run(argv, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def resolve_cap_path(board):
    rc, out, _ = ssh_cmd(board, 'find /sys/kernel/debug/ieee80211 -name agg_win_cap 2>/dev/null | head -1')
    p = out.strip()
    return p if rc == 0 and p else None


def read_hist(board, phyidx=1):
    """返回指定 phy band 的 aggr_stats 计数数组（Length/Count 分桶）。"""
    rc, out, _ = ssh_cmd(board, 'cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats')
    if rc != 0:
        return None
    counts = []
    for line in out.splitlines():
        s = line.strip()
        if s.startswith('Count:'):
            counts.append([int(x) for x in re.findall(r'\d+', s)])
    return counts[phyidx] if len(counts) > phyidx else None


def parse_first_interval_end(logfile):
    try:
        with open(logfile, 'r', encoding='utf-8', errors='replace') as f:
            for raw in f:
                m = LINE_RE.search(raw)
                if m:
                    return float(m.group(2))
    except FileNotFoundError:
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='192.168.1.1')
    ap.add_argument('--cap', type=int, default=2)
    ap.add_argument('--duration', type=int, default=125)
    ap.add_argument('--issue-sec', type=float, default=50.0)
    ap.add_argument('--out-prefix', default='ampdu_final')
    ap.add_argument('--iperf3', default=DEFAULT_IPERF3)
    args = ap.parse_args()

    logfile = os.path.join(HERE, args.out_prefix + '_iperf3.txt')
    events = os.path.join(HERE, args.out_prefix + '_events.json')
    png = os.path.join(HERE, args.out_prefix + '.png')
    hist_png = os.path.join(HERE, args.out_prefix + '_hist.png')
    csvf = os.path.join(HERE, args.out_prefix + '.csv')

    cap_path = resolve_cap_path(args.board)
    if not cap_path:
        print('[fail] 未找到 agg_win_cap 节点'); sys.exit(1)
    print('[path] %s' % cap_path)
    rc, out, _ = ssh_cmd(args.board, 'echo 0 > %s; cat %s' % (cap_path, cap_path))
    print('[reset] agg_win_cap = %s' % out.strip())
    ssh_cmd(args.board, 'dmesg -C')

    # 打流
    if os.path.exists(logfile):
        os.remove(logfile)
    iperf = subprocess.Popen(
        [args.iperf3, '-c', args.board, '-p', '5201', '-R',
         '-t', str(args.duration), '-i', '1', '--logfile', logfile, '--forceflush'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t_launch = time.perf_counter()
    print('[iperf3] pid=%d 日志=%s' % (iperf.pid, logfile))

    # 对齐原点
    origin = None
    deadline = t_launch + 10
    while time.perf_counter() < deadline and iperf.poll() is None:
        e = parse_first_interval_end(logfile)
        if e is not None:
            origin = time.perf_counter() - e
            break
        time.sleep(0.05)
    if origin is None:
        origin = t_launch; print('[warn] 未对齐，以启动为原点')
    else:
        print('[对齐] 原点=首区间结束 %.2fs' % e)

    def wait_until(t):
        while time.perf_counter() - origin < t and iperf.poll() is None:
            time.sleep(0.01)

    # 无限制区间快照
    wait_until(args.issue_sec - 8)
    hA0 = read_hist(args.board)
    wait_until(args.issue_sec - 4)
    hA1 = read_hist(args.board)
    print('[uncapped snapshots] %s / %s' % (sum(hA0) if hA0 else None, sum(hA1) if hA1 else None))

    # 定时下发
    wait_until(args.issue_sec)
    t_pre = time.perf_counter() - origin
    rc, out, err = ssh_cmd(args.board, 'echo %d > %s' % (args.cap, cap_path))
    t_issue = time.perf_counter() - origin
    print('[下发 t=%.3fs] echo %d rc=%d %s' % (t_issue, args.cap, rc, (err.strip() or '')))
    rc, out, _ = ssh_cmd(args.board, 'cat %s' % cap_path)
    print('[readback] %s' % out.strip())

    # 受限区间快照
    wait_until(args.issue_sec + 12)
    hB0 = read_hist(args.board)
    wait_until(args.issue_sec + 16)
    hB1 = read_hist(args.board)
    print('[capped snapshots] %s / %s' % (sum(hB0) if hB0 else None, sum(hB1) if hB1 else None))

    # 恢复
    wait_until(args.duration - 25)
    rc, out, _ = ssh_cmd(args.board, 'echo 0 > %s' % cap_path)
    print('[恢复] rc=%d' % rc)

    iperf.wait()
    print('[iperf3] 结束')

    rc, dmesg_out, _ = ssh_cmd(args.board, 'dmesg | grep -E "aggcap_dbg|agg_win_cap" | tail -40')
    dmesg_lines = [l for l in dmesg_out.splitlines() if l.strip()]
    print('[dmesg] %d 行' % len(dmesg_lines))

    d_unc = [b - a for a, b in zip(hA0 or [], hA1 or [])]
    d_cap = [b - a for a, b in zip(hB0 or [], hB1 or [])]

    meta = {
        'board': args.board, 'cap_path': cap_path, 'cap': args.cap,
        'duration_s': args.duration, 'issue_sec_target': args.issue_sec,
        'issue_sec_measured': round(t_issue, 3),
        'iperf3_log': logfile,
        'hist_uncapped_window': d_unc, 'hist_capped_window': d_cap,
        'hist_uncapped_sum': sum(d_unc), 'hist_capped_sum': sum(d_cap),
        'cap_bounds': CAPBOUNDS, 'cap_labels': CAPLABELS,
        'dmesg': dmesg_lines,
    }
    with open(events, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print('[events] %s' % events)

    # 时序图
    subprocess.run([sys.executable, PLOT, '--log', logfile, '--out', png, '--csv', csvf,
                    '--title', 'A-MPDU 聚合窗口实时下发时序图（5G 下行，t=%.1fs 窗口→%d）' % (t_issue, args.cap),
                    '--issue-sec', '%.3f' % t_issue])

    # 直方图对比图
    plot_hist(d_unc, d_cap, hist_png, args.cap, t_issue)
    print('DONE')


def plot_hist(d_unc, d_cap, out, cap, issue):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    rcParams['axes.unicode_minus'] = False
    n = min(len(d_unc), len(d_cap))
    if n == 0:
        print('[warn] 直方图数据缺失'); return
    su = sum(d_unc) or 1
    sc = sum(d_cap) or 1
    pu = [x * 100.0 / su for x in d_unc[:n]]
    pc = [x * 100.0 / sc for x in d_cap[:n]]
    x = range(n)
    w = 0.4
    fig, ax = plt.subplots(figsize=(11, 4.4), dpi=150)
    ax.bar([i - w / 2 for i in x], pu, w, label='窗口无限制（cap=256）', color='#1f5fbf')
    ax.bar([i + w / 2 for i in x], pc, w, label='窗口受限（cap=%d，t=%.1fs 起）' % (cap, issue), color='#d62b2b')
    ax.set_xticks(list(x))
    ax.set_xticklabels(CAPLABELS[:n], rotation=45, ha='right', fontsize=7)
    ax.set_xlabel('A-MPDU 聚合长度（MPDU 数，固件 tx_stats aggr_stats 分桶）')
    ax.set_ylabel('占比 (%)')
    ax.set_title('聚合窗口实时下发前后 · 固件 A-MPDU 长度分布对比（5G 下行）', fontsize=11)
    ax.grid(alpha=0.3, axis='y')
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(out)
    print('PNG: %s' % out)


if __name__ == '__main__':
    main()
