# -*- coding: utf-8 -*-
"""Baseline B receiver: UDP datagrams -> reassembly -> immediate decode.
No jitter buffer, no feedback, no playout scheduling.
"""
import argparse, time, sys, os, heapq, queue, threading, random
import av, cv2
import numpy as np
import rtc2


def pct(v, p):
    if not v:
        return 0.0
    s = sorted(v)
    return s[min(len(s) - 1, int(len(s) * p / 100.0))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=14)
    ap.add_argument('--port', type=int, default=9911)
    ap.add_argument('--out', default='udp_out.h264')
    ap.add_argument('--mp4', default='')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--expire', type=float, default=0.2)
    ap.add_argument('--rcvbuf', type=int, default=4 << 20)
    ap.add_argument('--drop-permille', type=int, default=0)
    ap.add_argument('--drop-seconds', type=float, default=1e9)
    ap.add_argument('--drop-every', type=int, default=0)
    ap.add_argument('--verbose', '-v', action='store_true')
    args = ap.parse_args()

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, args.rcvbuf)
    except Exception:
        pass
    s.bind(('', args.port))
    s.settimeout(0.05)
    print("udp receiver on :%d (rcvbuf=%d)" % (args.port, args.rcvbuf), flush=True)

    vdec = av.CodecContext.create('h264', 'r')
    writer = [None]
    dec_err = [0]
    dq = queue.Queue()
    dstat = {'n': 0}

    def decoder_worker():
        while True:
            data = dq.get()
            if data is None:
                break
            n = 0
            try:
                for pkt in vdec.parse(data):
                    for fr in vdec.decode(pkt):
                        n += 1
                        if args.mp4:
                            img = fr.to_ndarray(format='bgr24')
                            if writer[0] is None:
                                writer[0] = cv2.VideoWriter(
                                    args.mp4, cv2.VideoWriter_fourcc(*'mp4v'),
                                    float(args.fps), (img.shape[1], img.shape[0]))
                            writer[0].write(img)
            except Exception as e:
                dec_err[0] += 1
                if dec_err[0] <= 3:
                    print("WARN decode: %r" % (e,), flush=True)
            dstat['n'] += n

    dth = threading.Thread(target=decoder_worker, daemon=True)
    dth.start()

    fh = open(args.out, 'wb')
    pending = {}
    ok = lost = chunks = bytes_rx = dup = bad = padded = dropped = 0
    lat, asm, gaps = [], [], []
    prev_ok_t = None
    t0 = time.perf_counter()
    t_end = t0 + args.seconds
    last_report = t0

    while time.perf_counter() < t_end:
        try:
            data, addr = s.recvfrom(65535)
        except socket.timeout:
            data = None
        now = time.perf_counter()
        if data:
            try:
                h = rtc2.unpack_header(data)
            except Exception:
                bad += 1
                h = None
            if h is not None:
                body = data[rtc2.HDR_LEN:]
                want = h['payload_len']
                if len(body) >= want:
                    if len(body) > want:
                        padded += 1
                    body = body[:want]
                    if args.drop_every > 0 and h['seq'] % args.drop_every == 0:
                        dropped += 1
                        continue
                    if (args.drop_permille
                            and (now - t0) < args.drop_seconds
                            and random.randrange(1000) < args.drop_permille):
                        dropped += 1
                        continue
                    d = (int(now * 1e6) - h['send_ts_us']) & 0xFFFFFFFF
                    if d < 5000000:
                        lat.append(d / 1000.0)
                    chunks += 1
                    bytes_rx += len(body)
                    fid = h['frame_id']
                    ent = pending.get(fid)
                    if ent is None:
                        ent = {'c': {}, 'n': h['chunk_cnt'], 't': now,
                               'key': bool(h['flags'] & rtc2.F_KEYFRAME)}
                        pending[fid] = ent
                    if h['chunk_idx'] in ent['c']:
                        dup += 1
                    ent['c'][h['chunk_idx']] = body
                    if len(ent['c']) == ent['n']:
                        frame = b''.join(ent['c'][i] for i in range(ent['n']))
                        del pending[fid]
                        fh.write(frame)
                        ok += 1
                        asm.append((now - ent['t']) * 1000.0)
                        if prev_ok_t:
                            gaps.append((ent['t'] - prev_ok_t) * 1000.0)
                        prev_ok_t = ent['t']
                        dq.put(frame)
                        if args.verbose:
                            print("  fid=%-4d got=%d/%d asm=%5.1fms gap=%6.1fms"
                                  % (fid, ent['n'], ent['n'],
                                     asm[-1], gaps[-1] if gaps else 0.0), flush=True)
        for k in [k for k, v in pending.items() if now - v['t'] > args.expire]:
            pending.pop(k)
            lost += 1
        if now - last_report >= 1.0:
            el = now - t0
            print("  t=%4.1fs v=%d/%d chunks=%d rx=%.2fMbps dec=%d lat p50=%.0f/p95=%.0f"
                  % (el, ok, lost, chunks, bytes_rx * 8 / max(el, .001) / 1e6,
                     dstat['n'], pct(lat, 50), pct(lat, 95)), flush=True)
            last_report = now

    lost += len(pending)
    dq.put(None)
    dth.join(timeout=15.0)
    fh.close()
    s.close()
    if writer[0] is not None:
        writer[0].release()

    tot = ok + lost
    print("")
    print("RESULT udp ok=%d lost=%d frame_loss=%.2f%% chunks=%d dup=%d decoded=%d "
          "bad=%d padded=%d dropped=%d dec_err=%d"
          % (ok, lost, 100.0 * lost / max(tot, 1), chunks, dup, dstat['n'],
             bad, padded, dropped, dec_err[0]))
    print("one-way latency ms: p50=%.1f p95=%.1f p99=%.1f max=%.1f (n=%d)"
          % (pct(lat, 50), pct(lat, 95), pct(lat, 99), max(lat) if lat else 0.0, len(lat)))
    print("frame assemble ms: p50=%.1f p95=%.1f | arrival gap ms: p50=%.1f p95=%.1f"
          % (pct(asm, 50), pct(asm, 95), pct(gaps, 50), pct(gaps, 95)))
    print("wrote %s (%d bytes)" % (args.out, os.path.getsize(args.out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
