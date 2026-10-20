# -*- coding: utf-8 -*-
"""A-MPDU 聚合窗口实时修改时序验证实验（PC 端编排）。

补丁通道：mt7996 新增 per-station debugfs 写接口 agg_win_cap（0=不限, 1..256=BA窗口上限）。
写入即拆除活动 TX BA 会话并按新窗口重建（STA_REC_BA / WTBL_BA 重新下发固件）。

流程（与 run_mcs_timeline.py 同骨架）：
  1) 解析板上 agg_win_cap 路径，读取当前值（before，应为 0）；
  2) PC 起 iperf3 反向打流（下行），-i 1 按秒统计；
  3) t=issue-sec 时经 ssh 写入窗口上限，记录下发时刻（与 iperf3 同一时钟）；
  4) 下发前后各采一次 tx_stats 的 tx_ampdu_len 直方图（delta 见分布变化）；
  5) 结束后恢复 0，抓 dmesg 中 agg_win_cap 日志行作为固件侧证据；
  6) 调用 plot_edca_timeline.py 出图。

用法：
  python run_ampdu_timeline.py --cap 8 --issue-sec 50 --duration 100 --out-prefix ampdu_tl
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT = os.path.join(HERE, 'plot_edca_timeline.py')
DEFAULT_IPERF3 = r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+')
HIST_RE = re.compile(r'tx_ampdu_len:([\d-]+)\s+(\d+)')


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


def ssh_cmd(board, cmd, timeout=30):
    argv = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
            'root@%s' % board, cmd]
    r = subprocess.run(argv, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def resolve_cap_path(board):
    rc, out, err = ssh_cmd(board,
        'find /sys/kernel/debug/ieee80211 -name agg_win_cap 2>/dev/null | head -1')
    p = out.strip()
    return p if rc == 0 and p else None


def read_histogram(board):
    rc, out, err = ssh_cmd(board, 'cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats')
    if rc != 0:
        return None
    return {b: int(c) for b, c in HIST_RE.findall(out)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='192.168.1.1')
    ap.add_argument('--cap', type=int, default=8, help='BA 窗口上限（1..256）')
    ap.add_argument('--duration', type=int, default=100)
    ap.add_argument('--issue-sec', type=float, default=50.0)
    ap.add_argument('--out-prefix', default='ampdu_tl')
    ap.add_argument('--iperf3', default=DEFAULT_IPERF3)
    ap.add_argument('--no-restore', action='store_true')
    args = ap.parse_args()

    logfile = os.path.join(HERE, args.out_prefix + '_iperf3.txt')
    events = os.path.join(HERE, args.out_prefix + '_events.json')
    png = os.path.join(HERE, args.out_prefix + '.png')

    cap_path = resolve_cap_path(args.board)
    if not cap_path:
        print('[fail] 板上未找到 agg_win_cap（mt7996e.ko 未部署补丁版？）')
        sys.exit(1)
    print('[path] %s' % cap_path)
    rc, out, _ = ssh_cmd(args.board, 'cat %s' % cap_path)
    print('[before] agg_win_cap = %s' % out.strip())

    # iperf3 下行
    if os.path.exists(logfile):
        os.remove(logfile)
    iperf = subprocess.Popen(
        [args.iperf3, '-c', args.board, '-p', '5201', '-R',
         '-t', str(args.duration), '-i', '1', '--logfile', logfile,
         '--forceflush'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t_launch = time.perf_counter()
    print('[iperf3] 已启动 pid=%d 日志=%s' % (iperf.pid, logfile))

    origin = None
    deadline = t_launch + 10
    while time.perf_counter() < deadline and iperf.poll() is None:
        e = parse_first_interval_end(logfile)
        if e is not None:
            origin = time.perf_counter() - e
            break
        time.sleep(0.05)
    if origin is None:
        origin = t_launch
        print('[warn] 未捕获首条每秒行，以启动时刻为原点')
    else:
        print('[对齐] 原点已对齐（首区间结束=%.2fs）' % e)

    # 等 BA 会话建立并采下发前直方图
    while time.perf_counter() - origin < args.issue_sec - 2 and iperf.poll() is None:
        time.sleep(0.05)
    hist_before = read_histogram(args.board)

    # 定时下发
    while time.perf_counter() - origin < args.issue_sec and iperf.poll() is None:
        time.sleep(0.005)
    t_pre = time.perf_counter() - origin
    rc, out, err = ssh_cmd(args.board, 'echo %d > %s' % (args.cap, cap_path))
    t_issue = time.perf_counter() - origin
    print('[下发 t=%.3fs] echo %d rc=%d %s' % (t_issue, args.cap, rc, (err.strip() or '')))
    rc, out, _ = ssh_cmd(args.board, 'cat %s' % cap_path)
    print('[readback] agg_win_cap = %s' % out.strip())

    # 等窗口作用后采下发后直方图
    time.sleep(8)
    hist_after = read_histogram(args.board)

    iperf.wait()
    print('[iperf3] 结束')

    # 恢复 + dmesg 证据
    if not args.no_restore:
        rc, out, err = ssh_cmd(args.board, 'echo 0 > %s' % cap_path)
        print('[恢复] echo 0 rc=%d' % rc)
        time.sleep(1)
        rc, out, _ = ssh_cmd(args.board, 'cat %s' % cap_path)
        print('[restored] agg_win_cap = %s' % out.strip())
    rc, dmesg_out, _ = ssh_cmd(args.board, 'dmesg | grep agg_win_cap | tail -20')
    dmesg_lines = [l for l in dmesg_out.splitlines() if l.strip()]
    print('[dmesg] %d 行 agg_win_cap 日志' % len(dmesg_lines))

    meta = {
        'board': args.board, 'cap_path': cap_path, 'cap': args.cap,
        'duration_s': args.duration, 'issue_sec_target': args.issue_sec,
        'issue_sec_measured': round(t_issue, 3),
        'iperf3_log': logfile,
        'hist_before': hist_before, 'hist_after': hist_after,
        'dmesg': dmesg_lines,
        'align_method': ('first_interval_end' if origin != t_launch else 'launch_time'),
    }
    with open(events, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print('[events] %s' % events)

    plot_argv = [sys.executable, PLOT, '--log', logfile, '--out', png,
                 '--csv', os.path.join(HERE, args.out_prefix + '.csv'),
                 '--title', 'AMPDU 聚合窗口实时下发时序图（5G AP 下行，t=%.1fs 窗口→%d）' % (t_issue, args.cap),
                 '--issue-sec', '%.3f' % t_issue]
    subprocess.run(plot_argv)


if __name__ == '__main__':
    main()
