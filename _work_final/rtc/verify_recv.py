# -*- coding: utf-8 -*-
"""Minimal receiver/verifier for step 3: reassemble + integrity + decode check."""
import argparse, time, sys, collections
import av
import rtc2, l2sock


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=12)
    ap.add_argument('--iface', default='8852')
    ap.add_argument('--decode', action='store_true')
    args = ap.parse_args()

    sock = l2sock.L2Socket(dev_substr=args.iface, direction=l2sock.PCAP_D_IN)
    print("receiver on %s (direction=IN)" % sock.desc)

    dec = av.CodecContext.create('h264', 'r') if args.decode else None

    pending = collections.OrderedDict()
    frames_ok = frames_lost = chunks_rx = bytes_rx = dup = decoded = other = 0

    t0 = time.perf_counter()
    t_end = t0 + args.seconds
    last_report = t0
    while time.perf_counter() < t_end:
        r = sock.recv(0.02)
        if r is not None:
            ts, raw = r
            if len(raw) >= 14 and raw[12:14] == b"\x88\xb5":
                try:
                    h = rtc2.unpack_header(raw[14:])
                except rtc2.Rtc2Error:
                    h = None
                if h is not None:
                    body = raw[14 + rtc2.HDR_LEN:]
                    if len(body) == h['payload_len']:
                        chunks_rx += 1
                        bytes_rx += len(body)
                        fid = h['frame_id']
                        ent = pending.get(fid)
                        if ent is None:
                            ent = {'chunks': {}, 'cnt': h['chunk_cnt'],
                                   't0': time.perf_counter(),
                                   'key': bool(h['flags'] & rtc2.F_KEYFRAME),
                                   'pts': h['pts']}
                            pending[fid] = ent
                        if h['chunk_idx'] in ent['chunks']:
                            dup += 1
                        ent['chunks'][h['chunk_idx']] = body
                        now = time.perf_counter()
                        for f in [k for k, v in pending.items() if now - v['t0'] > 0.2]:
                            if len(pending[f]['chunks']) < pending[f]['cnt']:
                                frames_lost += 1
                            del pending[f]
                        if len(ent['chunks']) == ent['cnt'] and fid in pending:
                            data = b''.join(ent['chunks'][i] for i in range(ent['cnt']))
                            del pending[fid]
                            frames_ok += 1
                            if dec is not None:
                                try:
                                    for pkt in dec.parse(data):
                                        for fr in dec.decode(pkt):
                                            decoded += 1
                                except Exception:
                                    pass
            else:
                other += 1

        if time.perf_counter() - last_report >= 1.0:
            el = time.perf_counter() - t0
            print("  t=%4.1fs ok=%d lost=%d chunks=%d dup=%d rx=%.2f Mbps dec=%d other=%d"
                  % (el, frames_ok, frames_lost, chunks_rx, dup,
                     bytes_rx * 8 / max(el, 0.001) / 1e6, decoded, other))
            sys.stdout.flush()
            last_report = time.perf_counter()

    for k, v in pending.items():
        if len(v['chunks']) < v['cnt']:
            frames_lost += 1
    total = frames_ok + frames_lost
    print("RESULT: ok=%d lost=%d  frame_loss=%.2f%%  chunks=%d dup=%d  decode=%s"
          % (frames_ok, frames_lost, 100.0 * frames_lost / max(total, 1), chunks_rx, dup,
             ("%d frames" % decoded) if dec is not None else "off"))
    sock.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
