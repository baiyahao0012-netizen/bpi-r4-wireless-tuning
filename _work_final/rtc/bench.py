# -*- coding: utf-8 -*-
"""Repeatable A/B benchmark: conventional stack (RTC+UDP+IP) vs the new one (RTC only).

Both arms run the SAME sender.py / receiver.py with the SAME camera, encoder,
bitrate, pacing, jitter buffer, feedback and audio.  The only difference is
--transport, i.e. whether the RTC2 frame is carried in raw Ethernet frames or
inside a UDP/IP packet.

Runs are interleaved (arm order flips every repetition) so slow drift in the
radio environment cannot bias one arm.  Every run appends one row to raw.csv
immediately, so an interrupted batch still yields usable data.

    python bench.py --reps 5 --tag run1
"""
import argparse
import os
import re
import statistics
import subprocess
import sys
import time

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))

METRICS = [
    ('video_ok', 'ok'), ('video_lost', 'lost'), ('frame_loss_pct', '%'),
    ('chunks', 'n'), ('dup', 'n'), ('decoded', 'n'), ('dec_err', 'n'),
    ('other', 'n'), ('bad', 'n'),
    ('lat_p50', 'ms'), ('lat_p95', 'ms'), ('lat_p99', 'ms'), ('lat_max', 'ms'),
    ('asm_p50', 'ms'), ('asm_p95', 'ms'), ('gap_p50', 'ms'), ('gap_p95', 'ms'),
    ('relv_p50', 'ms'), ('relv_p95', 'ms'), ('rela_p50', 'ms'), ('rela_p95', 'ms'),
    ('jb_D', 'ms'), ('video_under', 'n'), ('audio_under', 'n'),
    ('audio_ok', 'n'), ('audio_lost', 'n'), ('audio_rms', ''),
    ('av_p50', 'ms'), ('av_p95', 'ms'), ('av_max', 'ms'),
    ('tx_frames', 'n'), ('tx_chunks', 'n'), ('tx_fps', 'fps'), ('tx_mbps', 'Mbps'),
    ('fb_reports', 'n'),
]

RES = {
    'video_ok': r'RESULT video ok=(\d+)',
    'video_lost': r'RESULT video ok=\d+ lost=(\d+)',
    'frame_loss_pct': r'frame_loss=([\d.]+)%',
    'chunks': r'frame_loss=[\d.]+% chunks=(\d+)',
    'dup': r'% chunks=\d+ dup=(\d+)',
    'decoded': r'dup=\d+ decoded=(\d+)',
    'dec_err': r'dec_err=(\d+)',
    'other': r'decoded=\d+ other=(\d+)',
    'bad': r'other=\d+ bad=(\d+)',
    'lat_p50': r'one-way latency ms: p50=([\d.]+)',
    'lat_p95': r'one-way latency ms: p50=[\d.]+ p95=([\d.]+)',
    'lat_p99': r'one-way latency ms: p50=[\d.]+ p95=[\d.]+ p99=([\d.]+)',
    'lat_max': r'one-way latency ms: p50=[\d.]+ p95=[\d.]+ p99=[\d.]+ max=([\d.]+)',
    'asm_p50': r'frame assemble ms: p50=([\d.]+)',
    'asm_p95': r'frame assemble ms: p50=[\d.]+ p95=([\d.]+)',
    'gap_p50': r'arrival gap ms: p50=([\d.]+)',
    'gap_p95': r'arrival gap ms: p50=[\d.]+ p95=([\d.]+)',
    'relv_p50': r'release interval video ms: p50=([\d.]+)',
    'relv_p95': r'release interval video ms: p50=[\d.]+ p95=([\d.]+)',
    'rela_p50': r'audio ms: p50=([\d.]+)',
    'rela_p95': r'audio ms: p50=[\d.]+ p95=([\d.]+)',
    'jb_D': r'jitter buffer: D=(\d+)ms',
    'video_under': r'video late=\d+ under=(\d+)',
    'audio_under': r'audio late=\d+ under=(\d+)',
    'audio_ok': r'audio ok=(\d+)',
    'audio_lost': r'audio ok=\d+ lost=(\d+)',
    'audio_rms': r'decoded_rms=([\d.]+)',
    'av_p50': r'A/V sync skew ms: p50=([\d.]+)',
    'av_p95': r'A/V sync skew ms: p50=[\d.]+ p95=([\d.]+)',
    'av_max': r'A/V sync skew ms: p50=[\d.]+ p95=[\d.]+ \|max\|=([\d.]+)',
    'tx_frames': r'done: (\d+) frames',
    'tx_chunks': r'done: \d+ frames, (\d+) chunks',
    'tx_fps': r'done: .*?([\d.]+) fps',
    'tx_mbps': r'done: .*?([\d.]+) Mbps avg',
    'fb_reports': r'feedback sent: (\d+) reports',
}


def parse(text):
    out = {}
    for k, pat in RES.items():
        m = re.search(pat, text)
        val = ''
        if m:
            try:
                val = float(m.group(1))
            except ValueError:
                val = ''
        out[k] = val
    return out


def run_one(arm, cond_args, cond_name, args, logdir):
    tag = '%s_%s_%02d' % (arm, cond_name, args._rep)
    h264 = os.path.join(logdir, tag + '.h264')
    rcmd = [PY, 'receiver.py', '--seconds', str(args.rx_seconds),
            '--transport', arm, '--out', h264] + cond_args
    scmd = [PY, 'sender.py', '--seconds', str(args.tx_seconds),
            '--bitrate', str(args.bitrate), '--audio', args.audio_mode,
            '--transport', arm]

    t0 = time.time()
    with open(os.path.join(logdir, tag + '.rx.log'), 'w', encoding='utf-8',
              errors='replace') as rf:
        rp = subprocess.Popen(rcmd, cwd=HERE, stdout=rf,
                              stderr=subprocess.STDOUT)
        time.sleep(args.warmup)
        with open(os.path.join(logdir, tag + '.tx.log'), 'w', encoding='utf-8',
                  errors='replace') as sf:
            try:
                subprocess.run(scmd, cwd=HERE, stdout=sf,
                               stderr=subprocess.STDOUT,
                               timeout=args.tx_seconds + 90)
            except subprocess.TimeoutExpired:
                pass
        try:
            rp.wait(timeout=args.rx_seconds + 60)
        except subprocess.TimeoutExpired:
            rp.kill()

    rtxt = ''
    try:
        with open(os.path.join(logdir, tag + '.rx.log'), encoding='utf-8',
                  errors='replace') as f:
            rtxt = f.read()
    except OSError:
        pass
    stxt = ''
    try:
        with open(os.path.join(logdir, tag + '.tx.log'), encoding='utf-8',
                  errors='replace') as f:
            stxt = f.read()
    except OSError:
        pass

    row = {'arm': arm, 'cond': cond_name, 'rep': args._rep,
           'elapsed_s': round(time.time() - t0, 2)}
    row.update(parse(rtxt))
    srow = parse(stxt)
    for k in ('tx_frames', 'tx_chunks', 'tx_fps', 'tx_mbps'):
        row[k] = srow[k]
    # extra bytes the conventional stack spends on IP+UDP headers
    # bytes the conventional stack must put on the air that the new one does
    # not: IPv4 (20) + UDP (8) per packet
    ch = row.get('tx_chunks') or 0
    row['hdr_bytes'] = int(ch * 28) if (ch and arm == 'udp') else 0
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reps', type=int, default=5)
    ap.add_argument('--arms', default='udp,l2')
    ap.add_argument('--conds', default='clean,lossy')
    ap.add_argument('--tx-seconds', type=int, default=9)
    ap.add_argument('--rx-seconds', type=int, default=12)
    ap.add_argument('--warmup', type=float, default=1.8)
    ap.add_argument('--bitrate', type=int, default=2500000)
    ap.add_argument('--drop-every', type=int, default=200)
    ap.add_argument('--audio-mode', default='tone',
                    choices=['tone', 'loopback', 'off'],
                    help='tone = identical synthesized audio in both arms '
                         '(loopback would couple with the receiver playback)')
    ap.add_argument('--gap', type=float, default=1.0)
    ap.add_argument('--tag', default='run')
    ap.add_argument('--outroot', default='bench')
    args = ap.parse_args()

    conds = {}
    for c in args.conds.split(','):
        if c == 'clean':
            conds[c] = []
        elif c == 'lossy':
            conds[c] = ['--drop-every', str(args.drop_every)]
        else:
            raise SystemExit('unknown condition ' + c)

    arms = args.arms.split(',')
    outdir = os.path.join(HERE, args.outroot, args.tag)
    logdir = os.path.join(outdir, 'logs')
    os.makedirs(logdir, exist_ok=True)
    csv_path = os.path.join(outdir, 'raw.csv')

    cols = ['arm', 'cond', 'rep', 'elapsed_s'] + [m[0] for m in METRICS] + ['hdr_bytes']
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        f.write(','.join(cols) + '\n')

    total = args.reps * len(arms) * len(conds)
    n = 0
    print('bench: %d runs -> %s' % (total, outdir), flush=True)
    for rep in range(1, args.reps + 1):
        args._rep = rep
        for cname, cargs in conds.items():
            order = arms if rep % 2 == 1 else list(reversed(arms))
            for arm in order:
                n += 1
                print('  [%2d/%2d] rep%d %-6s %-5s ... ' % (n, total, rep, arm, cname),
                      end='', flush=True)
                row = run_one(arm, cargs, cname, args, logdir)
                with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                    f.write(','.join(str(row.get(c, '')) for c in cols) + '\n')
                print('ok=%s lost=%s dec=%s p50=%s p95=%s under=%s'
                      % (row['video_ok'], row['video_lost'], row['decoded'],
                         row['lat_p50'], row['lat_p95'], row['video_under']),
                      flush=True)
                time.sleep(args.gap)

    summarise(csv_path, outdir, cols, args)


def summarise(csv_path, outdir, cols, args):
    import csv
    rows = []
    with open(csv_path, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append(r)

    def num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    groups = {}
    for r in rows:
        groups.setdefault((r['arm'], r['cond']), []).append(r)

    show = ['video_ok', 'video_lost', 'frame_loss_pct', 'chunks', 'decoded',
            'dec_err', 'other', 'bad', 'lat_p50', 'lat_p95', 'lat_p99',
            'asm_p95', 'gap_p95', 'relv_p95', 'jb_D', 'video_under',
            'audio_ok', 'audio_lost', 'audio_rms', 'av_p50', 'av_p95',
            'av_max', 'tx_frames', 'tx_fps', 'tx_mbps', 'fb_reports',
            'hdr_bytes']

    lines = []
    lines.append('bench summary  tag=%s  reps=%d  bitrate=%d  tx=%ds rx=%ds'
                 % (args.tag, args.reps, args.bitrate, args.tx_seconds,
                    args.rx_seconds))
    lines.append('')
    for (arm, cond) in sorted(groups):
        rs = groups[(arm, cond)]
        lines.append('%s / %s   n=%d' % (arm.upper(), cond, len(rs)))
        lines.append('  %-16s %12s %10s %10s %10s'
                     % ('metric', 'mean', 'std', 'min', 'max'))
        for m in show:
            vals = [num(r.get(m)) for r in rs]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            mean = statistics.fmean(vals)
            sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
            lines.append('  %-16s %12.2f %10.2f %10.2f %10.2f'
                         % (m, mean, sd, min(vals), max(vals)))
        lines.append('')

    # head-to-head on the metrics that decide the question
    lines.append('HEAD TO HEAD (mean, conventional=udp vs new=l2)')
    keys = ['video_lost', 'frame_loss_pct', 'decoded', 'dec_err', 'lat_p50',
            'lat_p95', 'asm_p95', 'gap_p95', 'relv_p95', 'video_under',
            'audio_lost', 'av_p95', 'tx_fps', 'hdr_bytes']
    for cond in sorted(set(r['cond'] for r in rows)):
        lines.append('')
        lines.append('  condition: %s' % cond)
        lines.append('  %-16s %12s %12s %10s' % ('metric', 'udp', 'l2', 'delta'))
        for k in keys:
            def gm(arm):
                vals = [num(r.get(k)) for r in groups.get((arm, cond), [])]
                vals = [v for v in vals if v is not None]
                return statistics.fmean(vals) if vals else None
            a, b = gm('udp'), gm('l2')
            if a is None or b is None:
                continue
            d = b - a
            pct = ('%+.1f%%' % (100.0 * d / a)) if a else 'n/a'
            lines.append('  %-16s %12.2f %12.2f %10s' % (k, a, b, pct))

    txt = '\n'.join(lines)
    print('')
    print(txt)
    with open(os.path.join(outdir, 'summary.txt'), 'w', encoding='utf-8') as f:
        f.write(txt + '\n')
    print('')
    print('raw data: %s' % csv_path)


if __name__ == '__main__':
    main()
