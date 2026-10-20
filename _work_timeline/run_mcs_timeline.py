# -*- coding: utf-8 -*-
"""MCS 实时修改时序验证实验（PC 端编排）：一边按秒统计，一边下发 MCS 速率限制，并记录下发时刻。

复用 run_edca_timeline.py 的编排骨架：
  1) 读取板端当前 station tx bitrate（before，供对照）；
  2) PC 起 iperf3 反向打流（下行），-i 1 按秒统计到日志；
  3) 在指定秒数 t_issue 通过 ssh 执行锁速命令（iw set bitrates），记录下发时刻（与 iperf3 同一时钟）；
  4) 打流结束，回读 station tx bitrate（after）确认命中，并恢复自动速率；
  5) 调用 plot_edca_timeline.py 出图。

用法：
  python run_mcs_timeline.py --station c0:35:32:19:cc:fb --issue-sec 50 --duration 100 --out-prefix mcs_tl
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT = os.path.join(HERE, 'plot_edca_timeline.py')
DEFAULT_IPERF3 = r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+')
BITRATE_RE = re.compile(r'tx bitrate:\s*([\d.]+)\s+MBit/s')

LOCK_CMD = 'iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0'
RESTORE_CMD = 'iw dev phy0.1-ap0 set bitrates'


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


def ssh_cmd(board, cmd, ssh_opts, timeout=30):
    argv = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10'] + ssh_opts + \
           ['root@%s' % board, cmd]
    r = subprocess.run(argv, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')


def read_tx_bitrate(board, station, ssh_opts):
    rc, out, err = ssh_cmd(board, 'iw dev phy0.1-ap0 station dump', ssh_opts)
    if rc != 0:
        return None
    m = BITRATE_RE.search(out)
    return float(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='192.168.1.1')
    ap.add_argument('--iface', default='phy0.1-ap0')
    ap.add_argument('--station', default='c0:35:32:19:cc:fb')
    ap.add_argument('--duration', type=int, default=100)
    ap.add_argument('--issue-sec', type=float, default=50.0)
    ap.add_argument('--out-prefix', default='mcs_timeline')
    ap.add_argument('--iperf3', default=DEFAULT_IPERF3)
    ap.add_argument('--ssh-opt', action='append', default=[])
    ap.add_argument('--no-restore', action='store_true', help='结束后不恢复自动速率')
    args = ap.parse_args()

    logfile = os.path.join(HERE, args.out_prefix + '_iperf3.txt')
    events = os.path.join(HERE, args.out_prefix + '_events.json')
    png = os.path.join(HERE, args.out_prefix + '.png')

    # 1) 读取板端当前速率（before）
    rate_before = read_tx_bitrate(args.board, args.station, args.ssh_opt)
    print('[before] station %s tx bitrate = %s Mbit/s' % (args.station, rate_before))

    # 2) 起 iperf3 反向打流
    if os.path.exists(logfile):
        os.remove(logfile)
    iperf = subprocess.Popen(
        [args.iperf3, '-c', args.board, '-p', '5201', '-R',
         '-t', str(args.duration), '-i', '1', '--logfile', logfile,
         '--forceflush'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t_launch = time.perf_counter()
    print('[iperf3] 已启动，pid=%d，日志=%s' % (iperf.pid, logfile))

    # 3) 对齐原点
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
        print('[warn] 未捕获首条每秒行，退回以启动时刻为原点')
    else:
        print('[对齐] iperf3 相对时间原点已对齐（首区间结束=%.2fs）' % e)

    # 4) 定时锁速
    t_issue = None
    while time.perf_counter() - origin < args.issue_sec and iperf.poll() is None:
        time.sleep(0.005)
    t_pre = time.perf_counter() - origin
    rc, out, err = ssh_cmd(args.board, LOCK_CMD, args.ssh_opt)
    print('[锁速 t=%.3fs] rc=%d %s%s' % (t_pre, rc, out.strip(), (' | ' + err.strip()) if err.strip() else ''))
    t_issue = time.perf_counter() - origin
    print('[时刻] 下发窗口 = %.3f ~ %.3f s（相对打流开始）' % (t_pre, t_issue))

    # 5) 等打流结束
    iperf.wait()
    t_end = time.perf_counter() - origin
    print('[iperf3] 结束，总时长 %.1fs' % t_end)

    # 6) 回读命中 + 恢复
    rate_after = read_tx_bitrate(args.board, args.station, args.ssh_opt)
    print('[after] 打流中 station tx bitrate = %s Mbit/s（锁速后）' % rate_after)
    if not args.no_restore:
        rc, out, err = ssh_cmd(args.board, RESTORE_CMD, args.ssh_opt)
        print('[恢复] 清除速率掩码 rc=%d %s%s' % (rc, out.strip(), (' | ' + err.strip()) if err.strip() else ''))
        time.sleep(1)
        rate_restored = read_tx_bitrate(args.board, args.station, args.ssh_opt)
        print('[restored] 恢复后 tx bitrate = %s Mbit/s' % rate_restored)
    else:
        rate_restored = None

    meta = {
        'board': args.board, 'iface': args.iface, 'station': args.station,
        'lock_cmd': LOCK_CMD, 'restore_cmd': RESTORE_CMD,
        'duration_s': args.duration, 'issue_sec_target': args.issue_sec,
        'issue_sec_measured': (round(t_issue, 3) if t_issue is not None else None),
        'iperf3_log': logfile,
        'tx_bitrate_before_mbps': rate_before,
        'tx_bitrate_after_mbps': rate_after,
        'tx_bitrate_restored_mbps': rate_restored,
        'align_method': ('first_interval_end' if origin is not None and origin != t_launch else 'launch_time'),
    }
    with open(events, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print('[events] %s' % events)

    # 7) 出图
    plot_argv = [sys.executable, PLOT, '--log', logfile, '--out', png,
                 '--csv', os.path.join(HERE, args.out_prefix + '.csv'),
                 '--title', 'MCS 实时下发时序图（5G AP 下行，t=%.1fs 锁速至最低档）' % (t_issue or 0)]
    if t_issue is not None:
        plot_argv += ['--issue-sec', '%.3f' % t_issue]
    subprocess.run(plot_argv)


if __name__ == '__main__':
    main()
