# -*- coding: utf-8 -*-
"""RTC2 receiver: dual-stream reassembly, jitter buffer, decode, A/V sync.

Video: chunks -> reassembly -> playout queue -> x264 decode -> mp4
Audio: chunks -> reassembly -> playout queue -> opus decode -> speaker

Usage:
    python receiver.py --seconds 16
    python receiver.py --seconds 16 --verbose
    python receiver.py --seconds 16 --jb 0 --no-audio-play
"""
import argparse, socket, time, sys, os, heapq, collections, queue, threading, random
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
    def __init__(self, clock, name, nom=None, hold_cap=None):
        # hold_cap: this stream refuses to be held longer than this, even if
        # the shared clock asks for more.  Audio must not inherit the video's
        # deep buffer: 200 ms of lip-sync headroom is 200 ms of added audio
        # latency, which is far more noticeable than a few dropped frames.
        self.hold_cap = hold_cap
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
        if self.hold_cap is not None and play - arrival > self.hold_cap:
            self.capped = getattr(self, 'capped', 0) + 1
            play = arrival + self.hold_cap
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
    ap.add_argument('--sync-port', type=int, default=9930)
    ap.add_argument('--out', default='recv_out.h264')
    ap.add_argument('--mp4', default='')
    ap.add_argument('--show', type=int, default=0,
                    help='1 = display decoded video in a live window (video-call view)')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--expire', type=float, default=0.2)
    ap.add_argument('--jb', type=int, default=1)
    ap.add_argument('--jb-min', type=float, default=40.0)
    ap.add_argument('--jb-max', type=float, default=200.0)
    ap.add_argument('--jb-audio', type=float, default=0.0,
                    help='max audio hold in ms; 0 = same as --jb-max')
    ap.add_argument('--fb', type=int, default=1)
    ap.add_argument('--fb-period', type=float, default=0.05)
    ap.add_argument('--fb-red', type=int, default=3)
    ap.add_argument('--fb-iface', default='GbE Family')
    ap.add_argument('--fb-dst', default='C0-35-32-19-CC-FB')
    ap.add_argument('--fb-src', default='40-C2-BA-52-70-95')
    ap.add_argument('--drop-permille', type=int, default=0)
    ap.add_argument('--drop-seconds', type=float, default=1e9)
    ap.add_argument('--burst', type=int, default=0,
                    help='1/N chance per frame of starting a 2-5 chunk burst loss')
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

    # ---- clock sync -------------------------------------------------------
    # The sender and receiver run on different hosts, so their perf_counter
    # epochs differ by an unknown constant.  Without it the one-way latency is
    # meaningless.  NTP-style exchange: SYN1(t1) -> SYN2(t_echo, t2, t3) -> t4.
    drop_seen = set()
    pli_sent = [0]
    last_pli = [0.0]
    burst_left = [0]
    rnd = random.Random(20261105)
    done_fids = set()
    max_done = [0]
    late_dup = 0
    fec_recovered = [0]
    nack_sent = [0]
    nack_tx = None
    if args.fb and args.transport == 'l2':
        try:
            nack_tx = txport.FbTx('l2', eth_dev=args.fb_iface,
                                  dst_mac=args.fb_dst, src_mac=args.fb_src,
                                  ethertype=rtc2.ETH_CONTROL)
        except Exception:
            nack_tx = None

    def _try_fec(ent):
        """Recover the single missing chunk as soon as it is provably missing."""
        miss = [i for i in range(ent['n']) if i not in ent['c']]
        if len(miss) != 1 or not ent['par'] or miss[0] == ent['n'] - 1:
            return False
        acc = bytearray(ent['par'])
        for _i, p in ent['c'].items():
            if len(p) > len(acc):
                acc.extend(b'\x00' * (len(p) - len(acc)))
            for j in range(len(p)):
                acc[j] ^= p[j]
        ent['c'][miss[0]] = bytes(acc)
        fec_recovered[0] += 1
        return True

    def _try_nack(ent, now):
        """Ask for the gap the moment it is visible, not after the timeout."""
        if nack_tx is None:
            return
        hi = max([i for i in ent['c'] if i != 0xFFFE], default=-1)
        # only ask for gaps we have not already asked for: re-requesting the
        # same chunk on every arriving neighbour is what caused the resend storm
        miss = [i for i in range(hi)
                if i not in ent['c'] and i not in ent['req']]
        if not miss or ent['nack_n'] >= 2:
            return
        if now - ent['last_nack'] < 0.015:
            return
        try:
            nack_tx.send(rtc2.pack_nack(
                [(ent['seq0'] + i) & 0xFFFF for i in miss]))
            nack_sent[0] += 1
            ent['nack_n'] += 1
            ent['last_nack'] = now
            ent['req'].update(miss)
        except Exception:
            pass

    sync_state = {'offset': None, 'rtt': 0, 'n': 0, 'dbg': 0}
    # Only our own arm gets the synchronised one-way measurement; the UDP/IP
    # arm is measured by its conventional RTT instead.
    if args.fb and args.transport == 'l2':
        def _sync_worker():
            try:
                stx = txport.FbTx('l2', eth_dev=args.fb_iface,
                                  dst_mac=args.fb_dst, src_mac=args.fb_src,
                                  ethertype=rtc2.ETH_CONTROL)
                srx = txport.CtrlRx('l2', iface=args.fb_iface)
            except Exception as e:
                print("WARN clock sync unavailable: %r" % (e,), flush=True)
                return
            best = None
            while True:
                t1 = int(time.perf_counter() * 1e6)
                try:
                    stx.send(rtc2.pack_sync(rtc2.SYNC_REQ, t1, 0, 0))
                except Exception:
                    pass
                t_end = time.perf_counter() + 1.0
                while time.perf_counter() < t_end:
                    p = srx.recv(0.05)
                    if not p:
                        continue
                    try:
                        sy = rtc2.unpack_sync(p)
                    except Exception:
                        continue
                    if sy['magic'] != rtc2.SYNC_RSP or sy['t_echo'] != t1:
                        continue
                    t4 = int(time.perf_counter() * 1e6)
                    t2, t3 = sy['t2'], sy['t3']
                    rtt = (t4 - t1) - (t3 - t2)
                    if rtt < 0:
                        continue
                    off = ((t2 - t1) + (t3 - t4)) // 2
                    # keep the sample with the smallest round trip: least
                    # asymmetry error, so the offset estimate is tightest
                    if best is None or rtt < best:
                        best = rtt
                        sync_state['offset'] = off
                        sync_state['rtt'] = rtt
                        sync_state['n'] += 1
        threading.Thread(target=_sync_worker, daemon=True).start()

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
    dec_err = [0]          # video decoder errors
    dec_err_a = [0]        # audio decoder errors
    pcm_fh = open(args.out_pcm, 'wb') if args.out_pcm else None
    dq = queue.Queue()
    dstat = {'n': 0}
    disp_q = queue.Queue(maxsize=2)     # decoded frames waiting to be shown

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
                        if args.mp4 or args.show:
                            img = fr.to_ndarray(format='bgr24')
                        if args.show:
                            try:
                                if disp_q.full():
                                    disp_q.get_nowait()
                                disp_q.put_nowait(img.copy())
                            except Exception:
                                pass
                        if args.mp4:
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
    aq = (PlayQueue(clock, 'audio', nom=0.020,
                    hold_cap=(args.jb_audio / 1000.0
                              if args.jb_audio > 0 else None))
          if (clock and args.audio) else None)

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
    last_send_ts = [0]            # echoed back so the sender can compute RTT
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
                        if (not is_audio and args.burst > 0
                                and h['seq'] not in drop_seen):
                            if burst_left[0] > 0:
                                burst_left[0] -= 1
                                drop_seen.add(h['seq'])
                                dropped += 1
                                continue
                            if rnd.random() < 1.0 / args.burst:
                                burst_left[0] = rnd.randint(1, 4)
                                drop_seen.add(h['seq'])
                                dropped += 1
                                continue
                        if (not is_audio and args.drop_every > 0
                                and h['seq'] % args.drop_every == 0
                                and h['seq'] not in drop_seen):
                            # impair each sequence number only once, otherwise
                            # the retransmission is dropped again and NACK
                            # never converges
                            drop_seen.add(h['seq'])
                            dropped += 1
                            continue
                        if (not is_audio and args.drop_permille
                                and (now - t0) < args.drop_seconds
                                and random.randrange(1000) < args.drop_permille):
                            dropped += 1
                            continue
                        a64 = int(now * 1e6)
                        _off = sync_state['offset']
                        if _off is None:
                            # same-host fallback: both clocks are the same epoch
                            d = (a64 - h['send_ts_us']) & 0xFFFFFFFF
                        else:
                            # lift the 32-bit sender stamp into our clock, then
                            # subtract the measured sender-receiver offset
                            # arrival expressed in the sender's clock
                            ref = a64 + _off
                            s_full = (ref & ~0xFFFFFFFF) | h['send_ts_us']
                            while s_full - ref > 0x80000000:
                                s_full -= 0x100000000
                            while ref - s_full > 0x80000000:
                                s_full += 0x100000000
                            d = a64 - s_full + _off
                        if not is_audio and 0 <= d < 5000000:
                            lat.append(d / 1000.0)
                        last_send_ts[0] = h['send_ts_us']
                        chunks_rx += 1
                        bytes_rx += len(body)
                        win_bytes += len(body)
                        fid = h['frame_id']
                        store = apending if is_audio else pending
                        # a retransmitted chunk of an already delivered frame
                        # used to resurrect it as a new, "incomplete" frame --
                        # which then triggered more NACKs.  Ignore those.
                        if not is_audio and (fid in done_fids
                                             or fid < max_done[0] - 64):
                            late_dup += 1
                            continue
                        if not is_audio and fid > max_fid:
                            max_fid = fid
                        ent = store.get(fid)
                        if ent is None:
                            ent = {'c': {}, 'n': h['chunk_cnt'], 't': now,
                                   'key': bool(h['flags'] & rtc2.F_KEYFRAME),
                                   'pts': h['pts'], 'lat': [], 'par': None,
                                   'seq0': (h['seq'] - h['chunk_idx']) & 0xFFFF,
                                   'nacked': False, 'nack_n': 0,
                                   'last_nack': 0.0, 'req': set()}
                            store[fid] = ent
                        if h['chunk_idx'] in ent['c']:
                            dup += 1
                        ent['c'][h['chunk_idx']] = body
                        if h['flags'] & rtc2.F_PARITY:
                            ent['par'] = ent['c'].pop(h['chunk_idx'])
                        ent['lat'].append(d / 1000.0)
                        if not (h['flags'] & rtc2.F_PARITY) and len(ent['c']) < ent['n']:
                            _try_fec(ent)
                            # the last chunk marks the point where every other
                            # chunk is either here or definitely lost, so this
                            # is when a request is both correct and cheap
                            if h['chunk_idx'] == ent['n'] - 1:
                                _try_nack(ent, now)
                        if len(ent['c']) == ent['n']:
                            data = b''.join(ent['c'][i] for i in range(ent['n']))
                            del store[fid]
                            if not is_audio:
                                done_fids.add(fid)
                                max_done[0] = max(max_done[0], fid)
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

        for _st in (pending, apending):
            for _k, _v in list(_st.items()):
                if len(_v['c']) < _v['n'] and now - _v['t'] > 0.015:
                    _try_nack(_v, now)

        for (store, is_a) in ((pending, False), (apending, True)):
            for k in [k for k, v in store.items() if now - v['t'] > args.expire]:
                v = store[k]
                miss = [i for i in range(v['n']) if i not in v['c']]
                # (a) FEC: one missing chunk is XOR-recoverable, but only when
                # it is not the last one (the last chunk may be short and its
                # true length is not recoverable from the parity).
                if len(miss) == 1 and v.get('par') and miss[0] != v['n'] - 1:
                    acc = bytearray(v['par'])
                    for i, p in v['c'].items():
                        if len(p) > len(acc):
                            acc.extend(b'\x00' * (len(p) - len(acc)))
                        for j in range(len(p)):
                            acc[j] ^= p[j]
                    v['c'][miss[0]] = bytes(acc)
                    fec_recovered[0] += 1
                    miss = []
                # (b) NACK: ask once, then give the retransmit one more window
                if miss and not v.get('nacked') and nack_tx is not None and not is_a:
                    try:
                        nack_tx.send(rtc2.pack_nack(
                            [(v['seq0'] + i) & 0xFFFF for i in miss]))
                        nack_sent[0] += 1
                    except Exception:
                        pass
                    v['nacked'] = True
                    v['t'] = now
                    continue
                if not miss:
                    # completed by FEC recovery or by retransmission
                    data = b''.join(v['c'][i] for i in range(v['n']))
                    del store[k]
                    if not is_a:
                        done_fids.add(k)
                        max_done[0] = max(max_done[0], k)
                    pts_s = v['pts'] / 90000.0
                    if is_a:
                        a_frames += 1
                        a_bytes += len(data)
                        if aq:
                            aq.push(pts_s, now, data, update=False)
                    else:
                        frames_ok += 1
                        win_ok += 1
                        if vq:
                            vq.push(pts_s, now, data)
                        else:
                            dq.put(data)
                    continue
                store.pop(k)
                # whole frame gone: FEC/NACK cannot help any more, the
                # reference chain is broken, so ask for a keyframe
                if not is_a and nack_tx is not None and now - last_pli[0] > 0.100:
                    try:
                        nack_tx.send(rtc2.pack_pli())
                        pli_sent[0] += 1
                        last_pli[0] = now
                    except Exception:
                        pass
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
                    dec_err_a[0] += 1
                    if dec_err_a[0] <= 3:
                        print("WARN audio decode: %r" % (e,), flush=True)

        if fb_sock and now - last_fb >= args.fb_period:
            wu = int((now - last_fb) * 1e6)
            tot_w = win_ok + win_lost
            loss_pm = int(1000.0 * win_lost / tot_w) if tot_w else 0
            jit_us = int(pct(clock.d, 95) * 1e6) if (clock and clock.d) else 0
            q_us = int(clock.D * 1000) if clock else 0
            payload = rtc2.pack_feedback(fb_seq, wu, win_bytes, q_us,
                                         min(loss_pm, 0xFFFF), min(jit_us, 0xFFFF),
                                         frames_ok, frames_lost, max(max_fid, 0),
                                         echo_ts=last_send_ts[0])
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

        if args.show:
            img = None
            try:
                while True:
                    img = disp_q.get_nowait()
            except queue.Empty:
                pass
            if img is not None:
                try:
                    cv2.imshow('RTC over WiFi', img)
                    cv2.waitKey(1)
                except Exception:
                    pass

    if args.show:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

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
    print("       audio ok=%d lost=%d bytes=%d decoded_samples=%d (%.2f s) dec_err_a=%d "
          "decoded_rms=%.1f"
          % (a_frames, a_lost, a_bytes, a_decoded, a_decoded / 48000.0, dec_err_a[0],
             (a_sum / max(a_cnt, 1)) ** 0.5))
    if sync_state['offset'] is not None:
        print("clock sync: offset=%+.3f ms  rtt=%.3f ms  samples=%d"
              % (sync_state['offset'] / 1000.0, sync_state['rtt'] / 1000.0,
                 sync_state['n']), flush=True)
    else:
        print("clock sync: NOT available (one-way latency unreliable)",
              flush=True)
    if fec_recovered[0] or nack_sent[0] or pli_sent[0]:
        print("recovery: fec_recovered=%d nack_sent=%d pli_sent=%d"
              % (fec_recovered[0], nack_sent[0], pli_sent[0]), flush=True)
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
