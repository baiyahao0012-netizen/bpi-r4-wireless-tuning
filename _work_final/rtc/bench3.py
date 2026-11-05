# -*- coding: utf-8 -*-
"""Strict A/B covering audio and ABR (the parts bench2 skipped).

Two arms carry the SAME RTC2 layer (framing, pacing, jitter buffer, feedback,
audio, ABR).  The ONLY difference is the transport:
    l2  : RTC2 frame straight into an Ethernet payload
    udp : RTC2 frame inside UDP, kernel adds IP/UDP headers

Conditions:
    clean_av       no loss, audio=loopback, ABR on
    lossy_av       1 fragment dropped every 200, audio=loopback, ABR on
    clean_av_abr0  no loss, audio=loopback, ABR off (isolates ABR cost)

Usage:
    python bench3.py --reps 2 --tag ab3
    python bench3.py --reps 1 --tag smoke --conds clean_av --arms l2 udp
"""
import csv
import os
import re
import statistics
import subprocess
import sys
import threading
import time

import ctl

REMOTE, RUSER, RPW = "192.168.240.221", "labuser", "[REDACTED-PWD]"
PY = r"D:\Bai_Yahao\Software\Python\python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
RX_SECS = 26
TX_SECS = 15
PING_IP = "192.168.240.162"
RX_WARMUP = 10.0   # audio+opus init makes the remote receiver slow to start

CONDS = {
    'clean_av':      {'drop': '', 'audio': 'loopback', 'abr': 1},
    'lossy_av':      {'drop': ' --drop-every 200', 'audio': 'loopback', 'abr': 1},
    'clean_av_abr0': {'drop': '', 'audio': 'loopback', 'abr': 0},
}

METRICS = [
    'ok', 'lost', 'frame_loss', 'chunks', 'decoded', 'dec_err',
    'audio_ok', 'audio_lost', 'audio_bytes', 'audio_dec_s',
    'jb_D', 'v_late', 'v_under', 'a_late', 'a_under',
    'rel_v_p50', 'rel_v_p95', 'rel_a_p50', 'rel_a_p95',
    'skew_p50', 'skew_p95', 'skew_max', 'skew_n',
    'lat_p50', 'lat_p95', 'asm_p95',
    'fb_sent', 'fb_rx', 'sync_rtt',
    'abr_sw', 'abr_up', 'abr_down', 'abr_final',
    'tx_frames', 'tx_mbps', 'tx_fps',
    'ping_min', 'ping_avg', 'ping_loss',
]

RES = {
    'ok':        r'RESULT video ok=(\d+)',
    'lost':      r'RESULT video ok=\d+ lost=(\d+)',
    'frame_loss': r'frame_loss=([\d.]+)%',
    'chunks':    r'frame_loss=[\d.]+% chunks=(\d+)',
    'decoded':   r'dup=\d+ decoded=(\d+)',
    'dec_err':   r'dec_err=(\d+)',
    'audio_ok':  r'audio ok=(\d+)',
    'audio_lost': r'audio ok=\d+ lost=(\d+)',
    'audio_bytes': r'audio ok=\d+ lost=\d+ bytes=(\d+)',
    'audio_dec_s': r'decoded_samples=\d+ \(([\d.]+) s\)',
    'jb_D':      r'jitter buffer: D=(\d+)ms',
    'v_late':    r'video late=(\d+)',
    'v_under':   r'video late=\d+ under=(\d+)',
    'a_late':    r'audio late=(\d+)',
    'a_under':   r'audio late=\d+ under=(\d+)',
    'rel_v_p50': r'release interval video ms: p50=([\d.]+)',
    'rel_v_p95': r'release interval video ms: p50=[\d.]+ p95=([\d.]+)',
    'rel_a_p50': r'audio ms: p50=([\d.]+)',
    'rel_a_p95': r'audio ms: p50=[\d.]+ p95=([\d.]+)',
    'skew_p50':  r'A/V sync skew ms: p50=([\d.]+)',
    'skew_p95':  r'A/V sync skew ms: p50=[\d.]+ p95=([\d.]+)',
    'skew_max':  r'p95=[\d.]+ \|max\|=([\d.]+)',
    'skew_n':    r'\|max\|=[\d.]+ \(n=(\d+)',
    'lat_p50':   r'one-way latency ms: p50=([\d.]+)',
    'lat_p95':   r'one-way latency ms: p50=[\d.]+ p95=([\d.]+)',
    'asm_p95':   r'frame assemble ms: p50=[\d.]+ p95=([\d.]+)',
    'fb_sent':   r'feedback sent: (\d+) reports',
    'fb_rx':     r'feedback: (\d+) reports',
    'sync_rtt':  r'clock sync: offset=[+-][\d.]+ ms  rtt=([\d.]+)',
    'abr_sw':    r'abr: (\d+) switches',
    'abr_up':    r'abr: \d+ switches \(\d+ up, (\d+) down',
    'abr_down':  r'abr: \d+ switches \((\d+) up',
    'abr_final': r'final (\d+) kbps',
    'tx_frames': r'done: (\d+) frames',
    'tx_mbps':   r'done: .*?([\d.]+) Mbps avg',
    'tx_fps':    r'done: .*?([\d.]+) fps',
    'ping_min':  r'Minimum = (\d+)ms',
    'ping_avg':  r'Average = (\d+)ms',
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
               "--fb-src E8-80-88-BA-3C-BB --audio 1 --out r_%s.h264" % tag)
    else:
        cmd = ("cd /d C:\\rtc & python receiver.py --transport udp --port 9922 "
               "--fb 1 --fb-iface I219 --fb-dst C0-35-32-19-CC-FB "
               "--fb-src E8-80-88-BA-3C-BB --audio 1 --out r_%s.h264" % tag)
    cmd += " --seconds %d --fps 15" % RX_SECS
    cmd += CONDS[cond]['drop']
    try:
        out, err, rc = ctl.run(REMOTE, cmd, RUSER, RPW, timeout=RX_SECS + 90)
        holder['rx'] = ctl.dec(out) + ctl.dec(err)
    except Exception as e:
        holder['rx'] = "REMOTE-ERROR %r" % (e,)


def run_one(arm, cond, rep):
    tag = "%s_%s_%02d" % (arm, cond, rep)
    holder = {'rx': ''}
    th = threading.Thread(target=run_rx, args=(arm, cond, tag, holder))
    th.start()
    time.sleep(RX_WARMUP)
    if arm == 'l2':
        sargs = [PY, 'sender.py', '--transport', 'l2',
                 '--dst', '08-9D-F4-CD-CC-42', '--src', '40-C2-BA-52-70-95',
                 '--fb-iface', '8852']
    else:
        sargs = [PY, 'sender.py', '--transport', 'udp',
                 '--dst-ip', '192.168.240.162', '--dst-port', '9922']
    sargs += ['--audio', CONDS[cond]['audio'],
              '--abr', str(CONDS[cond]['abr']),
              '--seconds', str(TX_SECS), '--bitrate', '2500000', '--fps', '15']
    tx = subprocess.run(sargs, cwd=HERE, capture_output=True, text=True,
                        encoding='utf-8', errors='replace', timeout=TX_SECS + 120)
    ping = subprocess.run(['ping', '-n', '10', PING_IP], cwd=HERE,
                          capture_output=True, text=True, encoding='gbk',
                          errors='replace', timeout=60)
    th.join(timeout=RX_SECS + 120)
    row = {'arm': arm, 'cond': cond, 'rep': rep}
    row.update(parse(holder['rx']))
    t = parse(tx.stdout + tx.stderr)
    for k in ('tx_frames', 'tx_mbps', 'tx_fps', 'abr_sw', 'abr_up',
              'abr_down', 'abr_final'):
        row[k] = t.get(k, '')
    p = parse(ping.stdout + ping.stderr)
    for k in ('ping_min', 'ping_avg', 'ping_loss'):
        row[k] = p.get(k, '')
    abr_lines = [ln for ln in (tx.stdout or '').splitlines() if 'ABR ' in ln]
    return row, abr_lines, (tx.stdout or '') + (tx.stderr or ''), holder['rx']


def main():
    reps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 2
    tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'ab3'
    conds = sys.argv[sys.argv.index('--conds') + 1].split(',') if '--conds' in sys.argv else list(CONDS)
    arms = sys.argv[sys.argv.index('--arms') + 1].split(',') if '--arms' in sys.argv else ['l2', 'udp']
    outdir = os.path.join(HERE, 'bench', tag)
    os.makedirs(outdir, exist_ok=True)
    csv_path = os.path.join(outdir, 'raw.csv')
    cols = ['arm', 'cond', 'rep'] + METRICS
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        f.write(','.join(cols) + '\n')

    total = reps * len(conds) * len(arms)
    n = 0
    for rep in range(1, reps + 1):
        for cond in conds:
            order = list(arms) if rep % 2 else list(reversed(arms))
            for arm in order:
                n += 1
                print('[%2d/%2d] rep%d %-3s %-14s ... ' % (n, total, rep, arm, cond),
                      end='', flush=True)
                row, abr_lines, txlog, rxlog = run_one(arm, cond, rep)
                tries = 0
                while float(row.get('ok') or 0) < 100 and tries < 2:
                    tries += 1
                    print('(retry %d) ' % tries, end='', flush=True)
                    time.sleep(3.0)
                    row, abr_lines, txlog, rxlog = run_one(arm, cond, rep)
                with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                    f.write(','.join(str(row.get(c, '')) for c in cols) + '\n')
                logname = os.path.join(outdir, '%s_%s_%02d.txt' % (arm, cond, rep))
                with open(logname, 'w', encoding='utf-8') as f:
                    f.write(txlog)
                    f.write('\n=== RECEIVER ===\n')
                    f.write(rxlog)
                print('ok=%s lost=%s audio=%s skew=%s abr=%s'
                      % (row.get('ok'), row.get('lost'), row.get('audio_lost'),
                         row.get('skew_p50'), row.get('abr_sw')), flush=True)
                time.sleep(3.0)

    rows = list(csv.DictReader(open(csv_path, encoding='utf-8')))

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    groups = {}
    for r in rows:
        groups.setdefault((r['arm'], r['cond']), []).append(r)
    keys = ['ok', 'lost', 'frame_loss', 'chunks', 'decoded', 'dec_err',
            'audio_ok', 'audio_lost', 'audio_dec_s', 'jb_D',
            'v_late', 'v_under', 'a_late', 'a_under',
            'rel_v_p50', 'rel_v_p95', 'rel_a_p50', 'rel_a_p95',
            'skew_p50', 'skew_p95', 'skew_max',
            'lat_p50', 'lat_p95', 'asm_p95', 'fb_sent', 'fb_rx',
            'abr_sw', 'abr_up', 'abr_down', 'abr_final',
            'tx_mbps', 'tx_fps', 'ping_avg']
    lines = ['A/B strict  reps=%d  tx=%ds  bitrate=2.5Mbps  audio=loopback' % (reps, TX_SECS), '']
    for cond in conds:
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


HOLDER = {}


def holder_txt(tag):
    return HOLDER.get(tag, '')


if __name__ == '__main__':
    main()
