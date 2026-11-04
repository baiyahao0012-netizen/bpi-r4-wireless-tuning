# -*- coding: utf-8 -*-
"""RTC2 receiver: dual-stream reassembly, jitter buffer, decode, A/V sync.

Video: chunks -> reassembly -> playout queue -> x264 decode -> mp4
Audio: chunks -> reassembly -> playout queue -> opus decode -> speaker

Usage:
    python receiver.py --seconds 16
    python receiver.py --seconds 16 --verbose
    python receiver.py --seconds 16 --jb 0 --no-audio-play
"""
import argparse, time, sys, os, heapq, collections, queue, threading, random
import av
import rtc2, l2sock, txport


def pct(v, p):
    if not v:
        return 0.0
    s = sorted(v)
    return s[min(len(s) - 1, int(len(s) * p / 100.0))]


class PlayoutClock(object):
    """One playout clock shared by the audio and video queues.

    play = arrival + D - (transit - tmin)  ==  pts + tmin + D

    The result is independent of each stream's own network delay, so a picture
    and the sound captured at that instant leave their queues at the same wall
    time.  Per-stream tmin would shift the two by the difference in their path
    delays, which would show up as a constant A/V skew.
    """

    def __init__(self, min_ms, max_ms, win=150):
        self.min_ms = float(min_ms)
        self.max_ms = float(max_ms)
        self.tmin = None
        self.d = collections.deque(maxlen=win)
        self.D = self.min_ms

    def play_for(self, pts_s):
        """Map a capture time onto the shared timeline without sampling it."""
        if self.tmin is None:
            return None
        return pts_s + self.tmin + self.D / 1000.0

    def stamp(self, pts_s, arrival):
        t = arrival - pts_s
        if self.tmin is None or t < self.tmin:
            self.tmin = t
        else:
            self.tmin += 2e-5          # let the floor follow clock drift up
        d = t - self.tmin
        if d < 0.0:
            d = 0.0
        self.d.append(d)
        if self.d:
            s = sorted(self.d)
            p95 = s[min(len(s) - 1, int(len(s) * 0.95))]
            self.D = min(self.max_ms, max(self.min_ms, p95 * 1250.0 + 20.0))
        return arrival + self.D / 1000.0 - d


class PlayQueue(object):
    def __init__(self, clock, name, nom=None):
        self.clock = clock
        self.name = name
        self.nom = nom
        self.q = []
        self.n = 0
        self.prev_play = None
        self.iv = []
        self.late = 0
        self.under = 0
        self.waited = []
        self.own = collections.deque(maxlen=400)

    def push(self, pts_s, arrival, payload, update=True):
        # Only the stream whose pts is anchored to the wall clock may move the
        # shared baseline.  A capture device running slow reports pts that fall
        # behind real time, which looks exactly like a growing queue and would
        # otherwise inflate D for every stream until it saturates.
        if update or self.clock.tmin is None:
            play = self.clock.stamp(pts_s, arrival)
        else:
            play = self.clock.play_for(pts_s)
            if play is None:
                play = self.clock.stamp(pts_s, arrival)
        self.own.append(arrival - pts_s)          # seconds
        if play <= arrival:
            self.late += 1
            play = arrival + 0.001
        self.n += 1
        self.waited.append(max(0.0, (play - arrival) * 1000.0))
        heapq.heappush(self.q, (play, self.n, pts_s, payload, arrival))
        return play

    def due(self, now):
        out = []
        while self.q and self.q[0][0] <= now:
            out.append(heapq.heappop(self.q))
        return out

    def note(self, play):
        if self.prev_play is not None and self.nom:
            iv = play - self.prev_play
            self.iv.append(iv * 1000.0)
            if iv > 1.6 * self.nom:
                self.under += 1
        self.prev_play = play


def pick_output_device():
    """Prefer a wired WASAPI sink; a Bluetooth headset adds 100+ ms of its own
    latency, which would be measured as A/V skew rather than transport delay."""
    try:
        import sounddevice as sd
    except Exception:
        return None
    # Virtual sinks (FxSound, Nahimic, VB-Audio) forward to whatever the system
    # default is -- which here is a Bluetooth headset -- so they must not win.
    bad = ('FxSound', 'Nahimic', 'Virtual', 'VB-Audio', 'VoiceMeeter', 'Bluetooth')
    best = None
    for i, d in enumerate(sd.query_devices()):
        if d['max_output_channels'] < 1:
            continue
        api = sd.query_hostapis(d['hostapi'])['name']
        if 'WASAPI' not in api:
            continue
        name = d['name']
        if any(b in name for b in bad):
            continue
        if 'Realtek' in name:
            return i
        if best is None:
            best = i
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=14)
    ap.add_argument('--transport', default='l2', choices=['l2', 'udp'],
                    help='l2 = RTC2 in raw Ethernet frames; udp = RTC2 in UDP/IP')
    ap.add_argument('--iface', default='8852')
    ap.add_argument('--port', type=int, default=9922)
    ap.add_argument('--bind-ip', default='')
    ap.add_argument('--fb-dst-ip', default='192.168.240.2')
    ap.add_argument('--fb-port', type=int, default=9923)
    ap.add_argument('--out', default='recv_out.h264')
    ap.add_argument('--mp4', default='')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--expire', type=float, default=0.2)
    ap.add_argument('--jb', type=int, default=1)
    ap.add_argument('--jb-min', type=float, default=40.0)
    ap.add_argument('--jb-max', type=float, default=200.0)
    ap.add_argument('--fb', type=int, default=1)
    ap.add_argument('--fb-period', type=float, default=0.05)
    ap.add_argument('--fb-red', type=int, default=3)
    ap.add_argument('--fb-iface', default='GbE Family')
    ap.add_argument('--fb-dst', default='C0-35-32-19-CC-FB')
    ap.add_argument('--fb-src', default='40-C2-BA-52-70-95')
    ap.add_argument('--drop-permille', type=int, default=0)
    ap.add_argument('--drop-seconds', type=float, default=1e9)
    ap.add_argument('--drop-every', type=int, default=0,
                    help='deterministically drop every Nth video chunk '
                         '(same impairment for every group under test)')
    ap.add_argument('--audio', type=int, default=1, help='1=receive and play audio')
    ap.add_argument('--out-dev', type=int, default=-1)
    ap.add_argument('--out-pcm', default='', help='also write decoded audio to .pcm')
    ap.add_argument('--verbose', '-v', action='store_true')
    args = ap.parse_args()

    V = args.verbose
    def dbg(m):
        if V:
            print(m, flush=True)

    t_sock = time.perf_counter()
    sock = txport.DataRx(args.transport, iface=args.iface, port=args.port,
                         bind_ip=args.bind_ip)
    print("receiver transport=%s on %s (open %.0f ms)  jitter_buffer=%s"
          % (args.transport, sock.desc, (time.perf_counter() - t_sock) * 1000,
             ("on [%.0f..%.0f ms]" % (args.jb_min, args.jb_max)) if args.jb else "OFF"),
          flush=True)

    fb_sock = None
    if args.fb:
        if args.transport == 'l2':
            fb_sock = txport.FbTx('l2', eth_dev=args.fb_iface,
                                  dst_mac=args.fb_dst, src_mac=args.fb_src)
            fb_desc = args.fb_dst
        else:
            fb_sock = txport.FbTx('udp', dst_ip=args.fb_dst_ip,
                                  dst_port=args.fb_port)
            fb_desc = '%s:%d' % (args.fb_dst_ip, args.fb_port)
        print("feedback -> %s every %.0f ms x%d"
              % (fb_desc, args.fb_period * 1000, args.fb_red), flush=True)

    import cv2
    import numpy as np

    vdec = av.CodecContext.create('h264', 'r')
    adec = None
    aout = None
    aq_pcm = queue.Queue(maxsize=200)
    out_dev = None
    if args.audio:
        adec = av.CodecContext.create('libopus', 'r')
        out_dev = args.out_dev if args.out_dev >= 0 else pick_output_device()
        try:
            import sounddevice as sd
            info = sd.query_devices(out_dev) if out_dev is not None else None
            rate = int(info['default_samplerate']) if info else 48000
            aout = sd.OutputStream(device=out_dev, samplerate=rate, channels=2,
                                   dtype='int16', blocksize=0)
            aout.start()
            print("audio out: dev=%s %d Hz  %s"
                  % (out_dev, rate, info['name'] if info else "default"), flush=True)
        except Exception as e:
            print("WARN audio output unavailable (%r); decoding only" % (e,), flush=True)
            aout = None

    def audio_out_worker():
        while True:
            pcm = aq_pcm.get()
            if pcm is None:
                break
            if aout is None:
                continue
            try:
                aout.write(np.repeat(pcm.reshape(-1, 1), 2, axis=1))
            except Exception:
                pass

    if args.audio:
        threading.Thread(target=audio_out_worker, daemon=True).start()

    writer = [None]
    dec_err = [0]
    pcm_fh = open(args.out_pcm, 'wb') if args.out_pcm else None
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

    clock = PlayoutClock(args.jb_min, args.jb_max) if args.jb else None
    vq = PlayQueue(clock, 'video', nom=1.0 / args.fps) if clock else None
    aq = PlayQueue(clock, 'audio', nom=0.020) if (clock and args.audio) else None

    fh = open(args.out, 'wb')
    pending = {}
    apending = {}
    frames_ok = frames_lost = chunks_rx = bytes_rx = dup = other = bad = decoded = 0
    pad = dropped = 0
    a_frames = a_bytes = a_decoded = a_lost = 0
    a_sum = 0.0
    a_cnt = 0
    win_bytes = win_ok = win_lost = 0
    fb_seq = fb_sent = 0
    last_fb = time.perf_counter()
    fb_hist = collections.deque(maxlen=max(1, args.fb_red))
    lat, asm, gaps = [], [], []
    play_lat = []
    av_skew = []
    a_hist = collections.deque(maxlen=60)
    max_fid = -1
    prev_ok_t = None
    last_report = time.perf_counter()
    t0 = time.perf_counter()
    t_end = t0 + args.seconds

    while time.perf_counter() < t_end:
        to = 0.02
        nxt = None
        for qq in (vq, aq):
            if qq and qq.q:
                nxt = qq.q[0][0] if nxt is None else min(nxt, qq.q[0][0])
        if nxt is not None:
            to = min(0.02, max(0.0005, nxt - time.perf_counter()))
        r = sock.recv(to)
        if r is not None and r[0] == 'other':
            other += 1
            r = None
        elif r is not None and r[0] == 'skip':
            bad += 1
            r = None
        now = time.perf_counter()

        if r is not None:
            ts, raw = r
            if True:
                try:
                    h = rtc2.unpack_header(raw)
                except rtc2.Rtc2Error:
                    bad += 1
                    if bad <= 3:
                        print("WARN bad RTC2 header (%d B)" % len(raw), flush=True)
                    h = None
                if h is not None:
                    body = raw[rtc2.HDR_LEN:]
                    want = h['payload_len']
                    if len(body) >= want:
                        if len(body) > want:
                            pad += 1
                        body = body[:want]
                        is_audio = (h['stream_id'] == rtc2.S_AUDIO)
                        if (not is_audio and args.drop_every > 0
                                and h['seq'] % args.drop_every == 0):
                            dropped += 1
                            continue
                        if (not is_audio and args.drop_permille
                                and (now - t0) < args.drop_seconds
                                and random.randrange(1000) < args.drop_permille):
                            dropped += 1
                            continue
                        d = (int(now * 1e6) - h['send_ts_us']) & 0xFFFFFFFF
                        if not is_audio and d < 5000000:
                            lat.append(d / 1000.0)
                        chunks_rx += 1
                        bytes_rx += len(body)
                        win_bytes += len(body)
                        fid = h['frame_id']
                        store = apending if is_audio else pending
                        if not is_audio and fid > max_fid:
                            max_fid = fid
                        ent = store.get(fid)
                        if ent is None:
                            ent = {'c': {}, 'n': h['chunk_cnt'], 't': now,
                                   'key': bool(h['flags'] & rtc2.F_KEYFRAME),
                                   'pts': h['pts'], 'lat': []}
                            store[fid] = ent
                        if h['chunk_idx'] in ent['c']:
                            dup += 1
                        ent['c'][h['chunk_idx']] = body
                        ent['lat'].append(d / 1000.0)
                        if len(ent['c']) == ent['n']:
                            data = b''.join(ent['c'][i] for i in range(ent['n']))
                            del store[fid]
                            pts_s = h['pts'] / 90000.0
                            if is_audio:
                                a_frames += 1
                                a_bytes += len(data)
                                if aq:
                                    aq.push(pts_s, now, data, update=False)
                                else:
                                    pass
                            else:
                                fh.write(data)
                                frames_ok += 1
                                win_ok += 1
                                a2 = (now - ent['t']) * 1000.0
                                asm.append(a2)
                                if prev_ok_t:
                                    gaps.append((ent['t'] - prev_ok_t) * 1000.0)
                                prev_ok_t = ent['t']
                                if vq:
                                    pt = vq.push(pts_s, now, data)
                                    dbg("  fid=%-4d got=%d/%d lat=%5.1f..%5.1fms "
                                        "asm=%5.1fms gap=%6.1fms key=%d -> hold %5.1fms"
                                        % (fid, len(ent['c']), ent['n'],
                                           min(ent['lat']), max(ent['lat']), a2,
                                           gaps[-1] if gaps else 0.0,
                                           1 if ent['key'] else 0,
                                           max(0.0, (pt - now) * 1000.0)))
                                else:
                                    dq.put(data)
                    else:
                        bad += 1
                        if bad <= 3:
                            print("WARN payload %d < declared %d (fid=%d idx=%d)"
                                  % (len(body), want, h['frame_id'], h['chunk_idx']),
                                  flush=True)
            else:
                other += 1

        for (store, is_a) in ((pending, False), (apending, True)):
            for k in [k for k, v in store.items() if now - v['t'] > args.expire]:
                v = store.pop(k)
                miss = [i for i in range(v['n']) if i not in v['c']]
                if is_a:
                    a_lost += 1
                else:
                    frames_lost += 1
                    win_lost += 1
                if V:
                    dbg("  %sfid=%-4d got=%d/%d MISS=%s expired"
                        % ("a" if is_a else "", k, v['n'] - len(miss), v['n'], miss))

        # ---- playout -----------------------------------------------------
        if vq:
            for play, _n, pts_s, payload, arrival in vq.due(now):
                vq.note(play)
                play_lat.append(max(0.0, (now - play) * 1000.0))
                dq.put(payload)
                if a_hist:
                    ap, apl = min(a_hist, key=lambda x: abs(x[0] - pts_s))
                    if abs(ap - pts_s) < 0.100:
                        av_skew.append((play - apl) * 1000.0)
                dbg("  >> video play pts=%.3fs held=%5.1fms late_by=%4.1fms"
                    % (pts_s, (play - arrival) * 1000.0, (now - play) * 1000.0))
        if aq:
            for play, _n, pts_s, payload, arrival in aq.due(now):
                aq.note(play)
                a_hist.append((pts_s, play))
                try:
                    for pkt in adec.parse(payload):
                        for fr in adec.decode(pkt):
                            pcm = fr.to_ndarray()
                            if pcm.ndim > 1:
                                pcm = pcm[0]
                            pcm_i = np.clip(pcm.astype('int32'), -32768, 32767)
                            if pcm.dtype.kind == 'f':
                                pcm_i = (np.clip(pcm, -1.0, 1.0) * 32767).astype('int16')
                            else:
                                pcm_i = pcm.astype('int16')
                            a_decoded += fr.samples
                            a_sum += float((pcm_i.astype(np.float64) ** 2).sum())
                            a_cnt += pcm_i.shape[0]
                            if pcm_fh is not None:
                                pcm_fh.write(pcm_i.tobytes())
                            try:
                                aq_pcm.put_nowait(pcm_i)
                            except queue.Full:
                                pass
                except Exception as e:
                    dec_err[0] += 1
                    if dec_err[0] <= 3:
                        print("WARN audio decode: %r" % (e,), flush=True)

        if fb_sock and now - last_fb >= args.fb_period:
            wu = int((now - last_fb) * 1e6)
            tot_w = win_ok + win_lost
            loss_pm = int(1000.0 * win_lost / tot_w) if tot_w else 0
            jit_us = int(pct(clock.d, 95) * 1e6) if (clock and clock.d) else 0
            q_us = int(clock.D * 1000) if clock else 0
            payload = rtc2.pack_feedback(fb_seq, wu, win_bytes, q_us,
                                         min(loss_pm, 0xFFFF), min(jit_us, 0xFFFF),
                                         frames_ok, frames_lost, max(max_fid, 0))
            fb_hist.append(payload)
            for p in fb_hist:
                try:
                    fb_sock.send(p)
                    fb_sent += 1
                except Exception as e:
                    print("WARN feedback send: %r" % (e,), flush=True)
                    break
            fb_seq += 1
            last_fb = now
            win_bytes = win_ok = win_lost = 0

        if now - last_report >= 1.0:
            el = now - t0
            extra = ""
            if clock:
                extra = " | jb D=%.0fms" % clock.D
            if av_skew:
                extra += " av=%+.0fms" % pct(av_skew[-30:], 50)
            print("  t=%4.1fs v=%d/%d a=%d chunks=%d rx=%.2fMbps dec=%d "
                  "lat p50=%.0f/p95=%.0f%s"
                  % (el, frames_ok, frames_lost, a_frames, chunks_rx,
                     bytes_rx * 8 / max(el, .001) / 1e6, dstat['n'],
                     pct(lat, 50), pct(lat, 95), extra), flush=True)
            last_report = now

    if vq:
        for play, _n, pts_s, payload, arrival in vq.due(time.perf_counter() + 1.0):
            dq.put(payload)
    frames_lost += len(pending)
    a_lost += len(apending)
    dq.put(None)
    dth.join(timeout=15.0)
    if args.audio:
        aq_pcm.put(None)
    time.sleep(0.1)
    decoded = dstat['n']
    fh.close()
    if pcm_fh is not None:
        pcm_fh.close()
    sock.close()
    if fb_sock:
        fb_sock.close()
    if aout is not None:
        try:
            aout.stop(); aout.close()
        except Exception:
            pass
    if writer[0] is not None:
        writer[0].release()

    tot = frames_ok + frames_lost
    print("")
    print("RESULT video ok=%d lost=%d frame_loss=%.2f%% chunks=%d dup=%d decoded=%d "
          "other=%d bad=%d padded=%d dropped=%d dec_err=%d q_left=%d"
          % (frames_ok, frames_lost, 100.0 * frames_lost / max(tot, 1),
             chunks_rx, dup, decoded, other, bad, pad, dropped,
             dec_err[0], dq.qsize()))
    print("       audio ok=%d lost=%d bytes=%d decoded_samples=%d (%.2f s) "
          "decoded_rms=%.1f"
          % (a_frames, a_lost, a_bytes, a_decoded, a_decoded / 48000.0,
             (a_sum / max(a_cnt, 1)) ** 0.5))
    print("one-way latency ms: p50=%.1f p95=%.1f p99=%.1f max=%.1f (n=%d)"
          % (pct(lat, 50), pct(lat, 95), pct(lat, 99), max(lat) if lat else 0.0, len(lat)))
    print("frame assemble ms: p50=%.1f p95=%.1f | arrival gap ms: p50=%.1f p95=%.1f"
          % (pct(asm, 50), pct(asm, 95), pct(gaps, 50), pct(gaps, 95)))
    if clock:
        print("jitter buffer: D=%.0fms  video late=%d under=%d  audio late=%d under=%d"
              % (clock.D, vq.late, vq.under, aq.late if aq else 0, aq.under if aq else 0))
        print("release interval video ms: p50=%.1f p95=%.1f | audio ms: p50=%.1f p95=%.1f"
              % (pct(vq.iv, 50), pct(vq.iv, 95),
                 pct(aq.iv, 50) if aq else 0.0, pct(aq.iv, 95) if aq else 0.0))
    if aq and aq.own and vq and vq.own:
        # Only the difference is meaningful: each stream's raw arrival-pts also
        # contains the offset between this host's perf_counter and the sender's.
        # A drifting difference means a capture clock is off, not the network.
        dv = pct(aq.own, 50) - pct(vq.own, 50)
        el = max(time.perf_counter() - t0, 1e-6)
        print("capture clock: audio-video transit drift %+.0f ms over %.0f s "
              "(%.2f%% -- a capture device running slow shows up here)"
              % (dv * 1000.0, el, 100.0 * dv / el))
    print("A/V sync skew ms: p50=%.1f p95=%.1f |max|=%.1f (n=%d, + = audio leads)"
          % (pct(av_skew, 50), pct(av_skew, 95),
             max((abs(x) for x in av_skew), default=0.0), len(av_skew)))
    if fb_sock:
        print("feedback sent: %d reports (%d frames on the wire)" % (fb_seq, fb_sent))
    print("wrote %s (%d bytes)%s"
          % (args.out, os.path.getsize(args.out), ("  +" + args.mp4) if writer[0] else ""))
    return 0


if __name__ == '__main__':
    sys.exit(main())
