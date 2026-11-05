# -*- coding: utf-8 -*-
"""Formal A/B: our L2 protocol vs the conventional UDP/IP stack.

Both arms carry the SAME RTC2 layer, the same camera, encoder, bitrate and
pacing.  Only the transport differs.  The UDP arm is an ordinary UDP
application: no extra ports, no custom side channels.

    python bench2.py --reps 3 --tag ab1
"""
import os
import re
import statistics
import subprocess
import sys
import time

import ctl

REMOTE, RUSER, RPW = "192.168.240.221", "labuser", "[REDACTED-PWD]"
PY = r"D:\Bai_Yahao\Software\Python\python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
RX_SECS = 20
TX_SECS = 15
PING_IP = "192.168.240.162"

METRICS = ['ok', 'lost', 'frame_loss', 'decoded', 'chunks', 'dec_err',
           'lat_p50', 'lat_p95', 'asm_p95', 'jb_D', 'under',
           'fb_sent', 'sync_off', 'sync_rtt',
           'tx_frames', 'tx_mbps', 'tx_fps', 'fb_rx',
           'ping_min', 'ping_avg', 'ping_loss']

RES = {
    'ok': r'RESULT video ok=(\d+)',
    'lost': r'RESULT video ok=\d+ lost=(\d+)',
    'frame_loss': r'frame_loss=([\d.]+)%',
    'decoded': r'dup=\d+ decoded=(\d+)',
    'chunks': r'frame_loss=[\d.]+% chunks=(\d+)',
    'dec_err': r'dec_err=(\d+)',
    'lat_p50': r'one-way latency ms: p50=([\d.]+)',
    'lat_p95': r'one-way latency ms: p50=[\d.]+ p95=([\d.]+)',
    'asm_p95': r'frame assemble ms: p50=[\d.]+ p95=([\d.]+)',
    'jb_D': r'jitter buffer: D=(\d+)ms',
    'under': r'video late=\d+ under=(\d+)',
    'fb_sent': r'feedback sent: (\d+) reports',
    'sync_off': r'offset=([+-][\d.]+) ms',
    'sync_rtt': r'clock sync: offset=[+-][\d.]+ ms\s+rtt=([\d.]+)',
    'tx_frames': r'done: (\d+) frames',
    'tx_mbps': r'done: .*?([\d.]+) Mbps avg',
    'tx_fps': r'done: .*?([\d.]+) fps',
    'fb_rx': r'feedback: (\d+) reports',
    'ping_min': r'Minimum = (\d+)ms',
    'ping_avg': r'Average = (\d+)ms',
    'ping_loss': r'\((\d+)% loss\)',
}


def parse(txt):
    out = {}
    for k, pat in RES.items():
        m = re.search(pat, txt)
        out[k] = float(m.group(1)) if m else ''
    return out


def run_rx(arm, cond, tag, holder):
    if arm == 'l2':
        cmd = ("cd /d C:\\rtc & python receiver.py --transport l2 --iface AX201 "
               "--fb 1 --fb-iface I219 --fb-dst C0-35-32-19-CC-FB "
               "--fb-src E8-80-88-BA-3C-BB --audio 0 --out r_%s.h264" % tag)
    else:
        cmd = ("cd /d C:\\rtc & python receiver.py --transport udp --port 9922 "
               "--fb 1 --fb-iface I219 --fb-dst C0-35-32-19-CC-FB "
               "--fb-src E8-80-88-BA-3C-BB --audio 0 --out r_%s.h264" % tag)
    cmd += " --seconds %d" % RX_SECS
    cmd += " --fps 15"
    if cond == 'lossy':
        cmd += " --drop-every 200"
    try:
        out, err, rc = ctl.run(REMOTE, cmd, RUSER, RPW, timeout=RX_SECS + 90)
        holder['rx'] = ctl.dec(out) + ctl.dec(err)
    except Exception as e:
        holder['rx'] = "REMOTE-ERROR %r" % (e,)


def run_one(arm, cond, rep):
    tag = "%s_%s_%02d" % (arm, cond, rep)
    holder = {'rx': ''}
    th = __import__('threading').Thread(target=run_rx, args=(arm, cond, tag, holder))
    th.start()
    time.sleep(3.0)
    if arm == 'l2':
        sargs = [PY, 'sender.py', '--transport', 'l2', '--dst', '08-9D-F4-CD-CC-42',
                 '--src', '40-C2-BA-52-70-95', '--fb-iface', '8852']
    else:
        sargs = [PY, 'sender.py', '--transport', 'udp',
                 '--dst-ip', '192.168.240.162', '--dst-port', '9922']
    sargs += ['--audio', 'off', '--seconds', str(TX_SECS), '--bitrate', '2500000',
              '--fps', '15']
    tx = subprocess.run(sargs, cwd=HERE, capture_output=True, text=True,
                        encoding='utf-8', errors='replace', timeout=TX_SECS + 120)
    ping = subprocess.run(['ping', '-n', '10', PING_IP], cwd=HERE,
                          capture_output=True, text=True, encoding='gbk',
                          errors='replace', timeout=60)
    th.join(timeout=RX_SECS + 120)
    row = {'arm': arm, 'cond': cond, 'rep': rep}
    row.update(parse(holder['rx']))
    t = parse(tx.stdout + tx.stderr)
    for k in ('tx_frames', 'tx_mbps', 'tx_fps', 'fb_rx'):
        row[k] = t.get(k, '')
    p = parse(ping.stdout + ping.stderr)
    for k in ('ping_min', 'ping_avg', 'ping_loss'):
        row[k] = p.get(k, '')
    return row


def main():
    reps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 3
    tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'ab'
    outdir = os.path.join(HERE, 'bench', tag)
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, 'raw.csv')
    cols = ['arm', 'cond', 'rep'] + METRICS
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        f.write(','.join(cols) + '\n')

    total = reps * 2 * 2
    n = 0
    for rep in range(1, reps + 1):
        for cond in ('clean', 'lossy'):
            order = ('l2', 'udp') if rep % 2 else ('udp', 'l2')
            for arm in order:
                n += 1
                print('[%2d/%2d] rep%d %-3s %-5s ... ' % (n, total, rep, arm, cond),
                      end='', flush=True)
                row = run_one(arm, cond, rep)
                # a short capture window means the camera was still busy from
                # the previous run; that sample is not comparable
                tries = 0
                while float(row.get('ok') or 0) < 150 and tries < 2:
                    tries += 1
                    print('(retry %d) ' % tries, end='', flush=True)
                    time.sleep(3.0)
                    row = run_one(arm, cond, rep)
                with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                    f.write(','.join(str(row.get(c, '')) for c in cols) + '\n')
                print('ok=%s lost=%s dec=%s lat50=%s rtt=%s'
                      % (row.get('ok'), row.get('lost'), row.get('decoded'),
                         row.get('lat_p50'), row.get('ping_avg')), flush=True)
                time.sleep(3.0)

    # summary
    import csv as _csv
    rows = list(_csv.DictReader(open(csv_path, encoding='utf-8')))

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    groups = {}
    for r in rows:
        groups.setdefault((r['arm'], r['cond']), []).append(r)
    lines = ['A/B summary  reps=%d  tx=%ds  bitrate=2.5Mbps' % (reps, TX_SECS), '']
    keys = ['ok', 'lost', 'frame_loss', 'decoded', 'chunks', 'dec_err',
            'lat_p50', 'lat_p95', 'asm_p95', 'jb_D', 'under', 'fb_sent',
            'tx_mbps', 'tx_fps', 'fb_rx', 'ping_min', 'ping_avg', 'ping_loss']
    for cond in ('clean', 'lossy'):
        lines.append('== %s ==' % cond)
        lines.append('  %-12s %14s %14s' % ('metric', 'l2(ours)', 'udp(conv)'))
        for k in keys:
            cells = []
            for arm in ('l2', 'udp'):
                vals = [num(r.get(k)) for r in groups.get((arm, cond), [])]
                vals = [v for v in vals if v is not None]
                cells.append('%8.2f±%-5.2f' % (statistics.fmean(vals),
                                               statistics.stdev(vals) if len(vals) > 1 else 0.0)
                             if vals else '        -    ')
            lines.append('  %-12s %14s %14s' % (k, cells[0], cells[1]))
        lines.append('')
    txt = '\n'.join(lines)
    print('\n' + txt)
    with open(os.path.join(outdir, 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write(txt + '\n')
    print('\nraw: %s' % csv_path)


if __name__ == '__main__':
    main()
