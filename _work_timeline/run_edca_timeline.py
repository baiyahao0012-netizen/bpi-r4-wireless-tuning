# -*- coding: utf-8 -*-
"""EDCA 时序验证实验（PC 端编排）：一边按秒统计，一边下发命令，并记录下发时刻。

它做四件事：
  1) 读取板端当前 EDCA（debugfs），供事后对照/回滚；
  2) PC 起 iperf3 反向打流（下行），-i 1 按秒统计到日志；
  3) 在指定秒数 t_issue 通过 ssh 下发 EDCA 参数，记录下发时刻（与 iperf3 同一时钟）；
  4) 收尾并调用 plot_edca_timeline.py 出图。

用法（示例）：
  python run_edca_timeline.py --issue-sec 50 --duration 100 --out-prefix edca_tl
  python run_edca_timeline.py --baseline --duration 60 --out-prefix edca_tl_base   # 对照组：不下发

依赖：Windows 上有 iperf3.exe；到板子的免密 ssh（密钥或 sshpass，且 dropbear 22 端口已恢复）。
"""
import argparse, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT = os.path.join(HERE, 'plot_edca_timeline.py')
DEFAULT_IPERF3 = r'C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe'
LINE_RE = re.compile(r'\[\s*\d+\]\s+([\d.]+)-([\d.]+)\s+sec\s+')


def parse_first_interval_end(logfile):
    """返回日志里第一条每秒数据行的区间结束时刻（通常 1.00），用于把 iperf3
    内部相对时间对齐到本地 perf_counter 原点。"""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', default='192.168.1.1')
    ap.add_argument('--iface', default='phy0.1-ap0')
    ap.add_argument('--params', default='0 1 3 7 0',
                    help='下发参数 "<AC> <aifs> <cwmin> <cwmax> <txop>"，默认 BE 激进档')
    ap.add_argument('--duration', type=int, default=100)
    ap.add_argument('--issue-sec', type=float, default=50.0)
    ap.add_argument('--baseline', action='store_true', help='对照组：打流但不下发')
    ap.add_argument('--out-prefix', default='edca_timeline')
    ap.add_argument('--iperf3', default=DEFAULT_IPERF3)
    ap.add_argument('--ssh-opt', action='append', default=[], help='额外 ssh 参数，可重复，如 -i C:\\key')
    ap.add_argument('--no-restore', action='store_true', help='结束后不恢复原 EDCA')
    args = ap.parse_args()

    logfile = os.path.join(HERE, args.out_prefix + '_iperf3.txt')
    events = os.path.join(HERE, args.out_prefix + '_events.json')
    png = os.path.join(HERE, args.out_prefix + '.png')

    # 1) 读取板端现有 EDCA
    edca_before = ''
    try:
        rc, out, err = ssh_cmd(args.board, 'cat /sys/kernel/debug/ieee80211/phy*/mt76/edca',
                               args.ssh_opt)
        edca_before = out.strip()
        print('[EDCA 当前]\n%s' % edca_before)
    except Exception as e:
        print('[warn] 读取板端 EDCA 失败：%s' % e)

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

    # 3) 对齐原点：等第一条每秒行出现
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
        print('[warn] 未捕获首条每秒行，退回以启动时刻为原点（可能存在约 ±0.3s 偏移）')
    else:
        print('[对齐] iperf3 相对时间原点已对齐（首区间结束=%.2fs）' % e)

    # 4) 定时下发
    t_issue = None
    if not args.baseline:
        while time.perf_counter() - origin < args.issue_sec and iperf.poll() is None:
            time.sleep(0.005)
        t_pre = time.perf_counter() - origin
        cmd = 'python3 /root/edca_set.py %s %s' % (args.iface, args.params)
        try:
            rc, out, err = ssh_cmd(args.board, cmd, args.ssh_opt)
            print('[下发 t=%.3fs] rc=%d %s%s' % (t_pre, rc, out.strip(), (' | ' + err.strip()) if err.strip() else ''))
        except Exception as e:
            print('[下发失败] t=%.3fs %s' % (t_pre, e))
        t_issue = time.perf_counter() - origin
        print('[时刻] 下发窗口 = %.3f ~ %.3f s（相对打流开始）' % (t_pre, t_issue))

    # 5) 等打流结束
    iperf.wait()
    t_end = time.perf_counter() - origin
    print('[iperf3] 结束，总时长 %.1fs' % t_end)

    # 6) 可选恢复
    edca_after = ''
    if not args.baseline and not args.no_restore and edca_before:
        print('[提示] 如需恢复下发前 EDCA，请按上面 [EDCA 当前] 的值重跑 edca_set.py')
    if not args.baseline:
        try:
            rc, out, err = ssh_cmd(args.board, 'cat /sys/kernel/debug/ieee80211/phy*/mt76/edca',
                                   args.ssh_opt)
            edca_after = out.strip()
        except Exception:
            pass

    meta = {
        'board': args.board, 'iface': args.iface, 'params': args.params,
        'duration_s': args.duration, 'baseline': args.baseline,
        'issue_sec_target': (None if args.baseline else args.issue_sec),
        'issue_sec_measured': (round(t_issue, 3) if t_issue is not None else None),
        'iperf3_log': logfile, 'edca_before': edca_before, 'edca_after': edca_after,
        'align_method': ('first_interval_end' if origin is not None and origin != t_launch else 'launch_time'),
    }
    with open(events, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print('[events] %s' % events)

    # 7) 出图
    plot_argv = [sys.executable, PLOT, '--log', logfile, '--out', png,
                 '--csv', os.path.join(HERE, args.out_prefix + '.csv'),
                 '--title', 'EDCA 实时下发时序图（t=%.1fs 下发，依据实测下发时刻）'
                            % (t_issue if t_issue is not None else 0)]
    if t_issue is not None:
        plot_argv += ['--issue-sec', '%.3f' % t_issue]
    subprocess.run(plot_argv)


if __name__ == '__main__':
    main()
