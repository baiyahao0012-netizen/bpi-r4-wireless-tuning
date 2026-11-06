# -*- coding: utf-8 -*-
"""Step 3: video sender.  Camera -> H.264 -> RTC2 chunks -> paced raw L2.

Usage:
    python sender.py --seconds 10
    python sender.py --seconds 10 --verbose     # per-frame + per-stage diagnostics

Diagnostics are deliberately chatty so that a stall can be attributed to one
stage (camera / convert / encode / chunk / send / pace) instead of guessed at.
"""
import argparse, socket, time, sys, threading, collections, queue
from fractions import Fraction
import cv2, av
import rtc2, l2sock, txport


class Gcc(object):
    """Loss + delay based rate controller driven by receiver feedback.

    libx264 refuses an in-place bit_rate change, so every accepted request costs
    a full encoder reopen and an IDR frame.  Switches are therefore gated on a
    magnitude threshold *and* a minimum interval: without both, the controller
    thrashes and the stream degrades into a sequence of keyframes.
    """

    def __init__(self, start_bps, min_bps, max_bps, min_interval=0.5,
                 min_delta=0.06):
        self.min = float(min_bps)
        self.max = float(max_bps)
        self.cur = float(max(self.min, min(self.max, start_bps)))
        self.jit = None            # ewma of excess-transit p95, ms
        self.hist = collections.deque(maxlen=40)   # ~2 s of raw samples
        self.base = 0.0            # rolling minimum of that window
        self.n = 0
        self.last_switch = 0.0
        self.min_interval = min_interval
        self.min_delta = min_delta
        self.reason = 'init'
        self.n_up = self.n_down = 0

    def on_feedback(self, fb, now):
        j = fb['jitter_us'] / 1000.0
        loss = fb['loss_permille'] / 1000.0
        self.n += 1
        if self.jit is None:
            self.jit = j
        else:
            self.jit = 0.85 * self.jit + 0.15 * j
        self.hist.append(j)
        # Absolute queueing delay says little: a path can sit at 30 ms forever
        # and that is not congestion.  What matters is how far the current
        # delay sits above its own recent floor, so a steady path always reads
        # over==0 and recovery is possible.
        self.base = min(self.hist)
        over = self.jit - self.base
        if self.n < 6:
            return None

        if loss > 0.08:
            want, why = self.cur * 0.85, 'loss %.1f%%' % (loss * 100)
        elif loss > 0.02:
            want, why = self.cur * 0.92, 'loss %.1f%%' % (loss * 100)
        elif over > 25.0:
            want, why = self.cur * 0.90, 'delay +%.0fms' % over
        elif loss < 0.005 and over < 12.0:
            want, why = self.cur * 1.12, 'clean loss=%.1f%% delay=+%.0fms' % (loss * 100, over)
        else:
            return None

        want = max(self.min, min(self.max, want))
        if now - self.last_switch < self.min_interval:
            return None
        if abs(want - self.cur) / max(self.cur, 1.0) < self.min_delta:
            return None
        old = self.cur
        self.cur = want
        self.last_switch = now
        self.reason = why
        if want > old:
            self.n_up += 1
        else:
            self.n_down += 1
        return want


class Pacer(object):
    """Spread bytes at a target bitrate on an absolute timeline.

    Anchoring to an absolute clock (instead of sleeping a fixed amount after
    every frame) is what stops the pacer from *adding* latency: the time the
    camera already spent producing the frame counts against the budget, so a
    source that is slower than the target is never slowed down further.  The
    pacer therefore only ever smooths bursts; it can never become the
    frame-rate ceiling.
    """

    def __init__(self, bps):
        # 30% headroom: libx264 overshoots its own bit_rate, and every chunk
        # carries 42 B of Ethernet + RTC2 header on the wire.
        self.bps = float(bps) * 1.3
        self.t0 = time.perf_counter()
        self.sent = 0
        self.slept = 0.0
        self._lk = threading.Lock()

    def set_rate(self, bps):
        # Re-anchor first so a rate change neither owes nor credits time.
        with self._lk:
            self.t0 = time.perf_counter() - self.sent * 8.0 / self.bps
            self.bps = float(bps) * 1.3

    def wait(self, nbytes):
        # Shared by the video and audio threads: audio is low rate so it barely
        # moves the timeline, but it must not be sent outside the budget.
        with self._lk:
            self.sent += nbytes
            ideal = self.t0 + self.sent * 8.0 / self.bps
        d = ideal - time.perf_counter()
        if d > 0.001:
            time.sleep(d)
            self.slept += d


class Meter(object):
    """Accumulates per-stage wall time so the hot spot is obvious."""

    def __init__(self):
        self.acc = {}
        self.n = 0

    def add(self, key, dt):
        self.acc[key] = self.acc.get(key, 0.0) + dt

    def bump(self):
        self.n += 1

    def line(self):
        if not self.n:
            return "(no frames)"
        tot = sum(self.acc.values()) or 1e-9
        parts = []
        for k in ('read', 'conv', 'enc', 'chunk', 'send', 'pace', 'tail'):
            v = self.acc.get(k, 0.0)
            parts.append("%s=%.2fms(%.0f%%)" % (k, v / self.n * 1000, 100 * v / tot))
        return " ".join(parts) + " | loop=%.2fms -> %.1f fps ceiling" % (
            tot / self.n * 1000, self.n / tot)

    def reset(self):
        self.acc.clear()
        self.n = 0


class SeqGen(object):
    """One RTC2 sequence space shared by the video and audio senders."""

    def __init__(self):
        self._n = 0
        self._lk = threading.Lock()

    def reserve(self, k):
        # Never let one reservation straddle the 16-bit wrap: a frame whose
        # chunks run 65534,65535,0,1 would break the header's u16 seq field.
        # Leave a small hole instead; gaps are harmless because reassembly is
        # driven by frame_id and chunk_idx, and NACK uses seq0 arithmetic.
        with self._lk:
            if k <= 0xFFFF and self._n + k > 0xFFFF:
                self._n = 0
            s = self._n
            self._n = (self._n + k) & 0xFFFF
            return s


class AudioSource(object):
    """20 ms int16 mono blocks from a microphone, or a synthetic tone.

    A callback is used rather than a blocking read: on this host the blocking
    read delivers ~1.5x slower than realtime, which would make the audio clock
    drift away from the video clock for reasons that have nothing to do with
    the network.
    """

    def __init__(self, mode, sr, dev=None, gain=1.0):
        self.sr = sr
        self.q = queue.Queue(maxsize=400)
        self.mode = mode
        self.gain = gain
        self.rate_meas = []
        self.n_samples = 0
        self._t0 = None
        self._sd = None
        self._stream = None
        if mode.startswith('file:'):
            self._file = mode[5:]
            threading.Thread(target=self._file_loop, daemon=True).start()
        elif mode == 'tone':
            self._thread = threading.Thread(target=self._tone_loop, daemon=True)
            self._thread.start()
        elif mode == 'loopback':
            # WASAPI loopback of the current default render endpoint: captures
            # whatever the machine is playing, without a virtual cable.
            import pyaudiowpatch as pa
            self._pa = pa.PyAudio()
            lb = self._pa.get_default_wasapi_loopback()
            self.src_name = "%s [loopback]" % lb['name']
            self._ch = min(2, int(lb['maxInputChannels']))
            self._rate = int(lb['defaultSampleRate'])
            if self._rate != self.sr:
                print("WARN loopback endpoint runs at %d Hz, requested %d Hz"
                      % (self._rate, self.sr), flush=True)
            self._st = self._pa.open(format=pa.paInt16, channels=self._ch,
                                     rate=self._rate, input=True,
                                     input_device_index=lb['index'],
                                     frames_per_buffer=self.sr // 50)
            threading.Thread(target=self._loopback_loop, daemon=True).start()
        else:
            import sounddevice as sd
            import numpy as np
            self._sd = sd
            self._np = np

            def cb(indata, frames, ti, status):
                a = indata[:, 0]
                if self.gain != 1.0:
                    a = (a.astype('float32') * self.gain).astype('int16')
                else:
                    a = a.copy()
                if self._t0 is None:
                    self._t0 = time.perf_counter()
                self.n_samples += frames
                try:
                    self.q.put_nowait(a)
                except queue.Full:
                    pass

            ch = 1 if (dev is None or self._probe_ch(dev) < 2) else 2
            self._stream = sd.InputStream(device=dev, samplerate=sr, channels=ch,
                                          dtype='int16', blocksize=0, callback=cb)
            self._stream.start()

    def _probe_ch(self, dev):
        return int(self._sd.query_devices(dev)['max_input_channels'])

    def _file_loop(self):
        """Use the media file's own audio track, paced in real time."""
        import numpy as np
        import av as _av
        blk = self.sr // 50                     # 20 ms
        while True:
            try:
                cont = _av.open(self._file)
                st = cont.streams.audio[0]
                res = _av.AudioResampler(format='s16', layout='mono', rate=self.sr)
            except Exception as e:
                print("ERROR file audio source: %r" % (e,), flush=True)
                return
            acc = np.zeros(0, dtype=np.int16)
            t_next = time.perf_counter()
            for fr in cont.decode(st):
                try:
                    outs = res.resample(fr)
                except Exception:
                    continue
                for rf in outs:
                    a = rf.to_ndarray().reshape(-1).astype(np.int16)
                    acc = np.concatenate([acc, a])
                    while len(acc) >= blk:
                        chunk, acc = acc[:blk], acc[blk:]
                        if self._t0 is None:
                            self._t0 = time.perf_counter()
                            t_next = self._t0
                        self.n_samples += blk
                        if self.gain != 1.0:
                            chunk = (chunk.astype('float32') * self.gain).astype('int16')
                        try:
                            self.q.put_nowait(chunk.copy())
                        except queue.Full:
                            pass
                        t_next += 0.020
                        d = t_next - time.perf_counter()
                        if d > 0:
                            time.sleep(d)
            cont.close()                        # loop to match the video

    def _loopback_loop(self):
        import numpy as np
        blk = self.sr // 50                     # 20 ms
        while True:
            try:
                buf = self._st.read(blk, exception_on_overflow=False)
            except Exception:
                time.sleep(0.01)
                continue
            a = np.frombuffer(buf, dtype=np.int16)
            if self._ch > 1:
                a = a.reshape(-1, self._ch).mean(axis=1).astype(np.int16)
            else:
                a = a.copy()
            if self.gain != 1.0:
                a = np.clip(a.astype('float32') * self.gain,
                            -32768, 32767).astype(np.int16)
            try:
                self.q.put_nowait(a)
            except queue.Full:
                pass

    def _tone_loop(self):
        # One second of tone, sliced per block: recomputing the sinusoid 50
        # times a second burns CPU that the video encoder needs.
        import numpy as np
        blk = self.sr // 50                     # 20 ms
        t = np.arange(self.sr) / float(self.sr)
        env = 0.35 + 0.25 * np.sin(2 * np.pi * 0.7 * t)
        self._tone = (env * 9000 * np.sin(2 * np.pi * 440.0 * t)).astype(np.int16)
        self._pos = 0
        t0 = time.perf_counter()
        n = 0
        while True:
            p = self._pos
            a = self._tone[p:p + blk]
            if len(a) < blk:
                a = np.concatenate([a, self._tone[:blk - len(a)]])
            self._pos = (p + blk) % self.sr
            n += blk
            try:
                self.q.put_nowait(a.copy())
            except queue.Full:
                pass
            nxt = t0 + n / float(self.sr)
            d = nxt - time.perf_counter()
            if d > 0:
                time.sleep(d)

    def read(self, timeout=0.5):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        if self._stream is not None:
            try:
                self._stream.stop(); self._stream.close()
            except Exception:
                pass
        if getattr(self, '_st', None) is not None:
            try:
                self._st.stop_stream(); self._st.close()
            except Exception:
                pass
        if getattr(self, '_pa', None) is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass


def build_encoder(w, h, fps, bitrate):
    c = av.CodecContext.create('libx264', 'w')
    c.width, c.height, c.pix_fmt = w, h, 'yuv420p'
    c.time_base = Fraction(1, fps)
    c.bit_rate = int(bitrate)
    # maxrate/bufsize matter more than bit_rate: without a VBV the encoder
    # wildly overshoots on IDR frames, so a lowered target never shows up on
    # the wire and the pacer then throttles the frame rate instead.
    c.options = {'preset': 'veryfast', 'tune': 'zerolatency',
                 'g': str(max(2, fps * 2)), 'sc_threshold': '0',
                 'maxrate': str(int(bitrate * 1.2)),
                 'bufsize': str(int(bitrate * 0.5))}
    c.open()
    return c


def is_key(pkt):
    try:
        return bool(pkt.is_keyframe)
    except Exception:
        pass
    b = bytes(pkt)
    i = 0
    while i + 4 < len(b):
        if b[i] == 0 and b[i+1] == 0 and b[i+2] == 1:
            t = b[i+3] & 0x1F
            if t in (5, 7):
                return True
            i += 3
        else:
            i += 1
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=10)
    ap.add_argument('--bitrate', type=int, default=2000000)
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--video', default='',
                    help='use this file as the video source instead of the camera')
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--height', type=int, default=480)
    ap.add_argument('--dst', default='C0-35-32-19-CC-FB')
    ap.add_argument('--src', default='40-C2-BA-52-70-95')
    ap.add_argument('--transport', default='l2', choices=['l2', 'udp'],
                    help='l2 = RTC2 straight into Ethernet frames (no IP/UDP); '
                         'udp = RTC2 inside UDP/IP, i.e. the conventional stack')
    ap.add_argument('--iface', default='GbE Family')
    ap.add_argument('--dst-ip', default='192.168.240.147')
    ap.add_argument('--dst-port', type=int, default=9922)
    ap.add_argument('--src-ip', default='192.168.240.2')
    ap.add_argument('--fb-port', type=int, default=9923)
    ap.add_argument('--fec', type=int, default=0,
                    help='1 = emit one XOR parity chunk per video frame')
    ap.add_argument('--cache-ms', type=int, default=3000,
                    help='how long sent chunks are kept for NACK retransmission')
    ap.add_argument('--mac-ctl', type=int, default=0,
                    help='1 = receive MAC-layer reports from the AP agent')
    ap.add_argument('--mac-port', type=int, default=9931)
    ap.add_argument('--sync-port', type=int, default=9930,
                    help='UDP port for the NTP-style clock-sync responder '
                         '(measurement only, identical for both A/B arms)')
    ap.add_argument('--chunk', type=int, default=rtc2.DEFAULT_CHUNK)
    ap.add_argument('--fb', type=int, default=1, help='1=listen for feedback')
    ap.add_argument('--fb-iface', default='8852',
                    help='adapter the reflected feedback arrives on')
    ap.add_argument('--abr', type=int, default=0,
                    help='1=GCC rate control. Off by default because every '
                         'rate switch reopens the encoder and inserts an IDR, '
                         'which is only worth paying for when it is wanted')
    ap.add_argument('--min-rate', type=int, default=1200000)
    ap.add_argument('--audio', default='mic',
                    choices=['mic', 'loopback', 'tone', 'off', 'file'],
                    help='loopback = WASAPI capture of what this machine is '
                         'playing (system sound); tone = synthetic 440 Hz')
    ap.add_argument('--audio-file', default='',
                    help='audio track source when --audio file (defaults to --video)')
    ap.add_argument('--audio-dev', type=int, default=-1)
    ap.add_argument('--audio-rate', type=int, default=48000)
    ap.add_argument('--audio-bitrate', type=int, default=64000)
    ap.add_argument('--audio-gain', type=float, default=1.0)
    ap.add_argument('--audio-pts', default='wall', choices=['wall', 'samples'],
                    help='wall = stamp audio with the same wall clock as video '
                         '(robust when a capture device does not run at exactly '
                         'realtime); samples = textbook sample-count clock')
    ap.add_argument('--max-rate', type=int, default=6000000)
    ap.add_argument('--verbose', '-v', action='store_true',
                    help='per-frame log + per-stage timing each second')
    args = ap.parse_args()

    V = args.verbose
    def dbg(msg):
        if V:
            print(msg, flush=True)

    # ---- camera -----------------------------------------------------------
    tc = time.perf_counter()
    if args.video:
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            print("ERROR: cannot open video file %r" % args.video); return 2
    else:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("ERROR: camera open failed (CAP_DSHOW, index 0)"); return 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    af = cap.get(cv2.CAP_PROP_FPS)
    dbg("camera open %.0f ms -> requested %dx%d@%d, actual %dx%d@%.1f"
        % ((time.perf_counter() - tc) * 1000, args.width, args.height,
           args.fps, aw, ah, af))
    for _ in range(5):                      # flush the driver's first frames
        cap.read()
    dbg("camera warm-up done (5 frames discarded)")

    # ---- encoder ----------------------------------------------------------
    te = time.perf_counter()
    enc = build_encoder(args.width, args.height, args.fps, args.bitrate)
    dbg("encoder open %.0f ms  libx264 %dx%d@%d %.0f kbps"
        % ((time.perf_counter() - te) * 1000, args.width, args.height,
           args.fps, args.bitrate / 1000.0))

    cur_rate = args.bitrate
    gcc = Gcc(cur_rate, args.min_rate, args.max_rate)
    switch_req = []                 # [target_bps, reason]
    sw_lock = threading.Lock()
    abr_log = []

    # ---- socket -----------------------------------------------------------
    ts0 = time.perf_counter()
    txp = txport.DataTx(args.transport, eth_dev=args.iface,
                        dst_mac=args.dst, src_mac=args.src,
                        dst_ip=args.dst_ip, dst_port=args.dst_port,
                        src_ip=args.src_ip)
    dbg("transport open %.0f ms  %s" % ((time.perf_counter() - ts0) * 1000, txp.desc))

    # Npcap handles are not thread safe: the data path and the clock-sync
    # responder both transmit on the same adapter.
    send_lk = threading.Lock()

    # Feedback arrives on the radio (the board reflects it out the Wi-Fi port),
    # so it needs its own capture handle.  A thread keeps it off the send path:
    # polling inside the frame loop would cost ~1 ms of pacing accuracy.
    fbrx = None
    fcache = {}                     # seq -> (chunk bytes, send time) for NACK
    resent = [0]
    fec_sent = [0]
    fec_err = [0]
    pkt_id = [0]
    force_idr = [False]
    pli_rx = [0]
    mac = {'rx': 0, 'last': None, 'seq': 0}
    last_change = [0.0]

    if args.mac_ctl:
        def _mac_listener():
            # The AP's busybox nc is TCP-only, so the report channel is a
            # short-lived TCP connection per sample rather than UDP.
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                srv.bind(('0.0.0.0', args.mac_port))
                srv.listen(16)
            except Exception as e:
                print("ERROR mac listener: %r" % (e,), flush=True)
                return
            while True:
                try:
                    conn, _peer = srv.accept()
                except Exception:
                    continue
                try:
                    conn.settimeout(1.0)
                    data = conn.recv(512)
                except Exception:
                    data = b''
                finally:
                    conn.close()
                t = data.decode('ascii', 'replace').strip()
                if not t.startswith('MACR,'):
                    continue
                p = t.split(',')
                try:
                    v = [int(x) for x in p[1:9]]
                except Exception:
                    continue
                if len(v) < 8:
                    continue
                mac['last'] = v
                mac['rx'] += 1
                mac['seq'] = v[0]

        threading.Thread(target=_mac_listener, daemon=True).start()
        print("mac reports on tcp/%d (%.0f ms)" % (args.mac_port, 100.0),
              flush=True)

        def _mac_ctrl():
            """Rate control driven by MAC-layer state.

            AQL measures what our own queueing costs in airtime.  Retries
            measure what the medium costs.  A backlog with few retries means
            we are sending too fast; a backlog with many retries means the
            channel is contested and dropping our rate would only make the
            picture worse while not freeing any airtime.
            """
            prev = None
            tgt = [None]        # last rate we asked for; cur_rate lags by a frame
            while True:
                time.sleep(0.1)
                v = mac['last']
                if v is None:
                    continue
                now = time.perf_counter()
                if prev is None:
                    prev = (v, now, sent_chunks)
                    continue
                pv, pt, pc = prev
                dt = max(1e-3, now - pt)
                # v = [aql_total, tx_pkts, tx_bytes, tx_duration, retries, failed]
                d_pkts = max(0, v[1] - pv[1])
                if d_pkts <= 0:
                    continue
                d_bytes = max(0, v[2] - pv[2])
                d_dur = max(0, v[3] - pv[3])
                d_ret = max(0, (v[4] - pv[4]) + (v[5] - pv[5]))
                prev = (v, now, sent_chunks)
                q_us = float(v[0])
                lim = 24000.0
                rr = (d_ret / d_pkts) if d_pkts > 0 else 0.0
                # airtime per kilobyte actually delivered: rises when the
                # medium itself is expensive, unlike a plain queue backlog
                cost = (d_dur / (d_bytes / 1024.0)) if d_bytes > 0 else 0.0
                d_total = max(0, v[6] - pv[6])
                share = (d_dur / d_total) if d_total > 0 else 0.0
                # attribution: how much of the station's airtime can be
                # explained by our own video flow at the current PHY rate.
                # A low value means the backlog is caused by something else
                # sharing the same station, and cutting our rate would not
                # free any airtime.
                d_our = max(0, sent_chunks - pc) * args.chunk
                phy_mbps = v[7] / 10.0
                pred_us = (d_our * 8.0 / phy_mbps) if phy_mbps > 1.0 else 0.0
                attr = (pred_us / d_dur) if d_dur > 0 else 0.0
                mac['cost'] = cost
                mac['share'] = share
                mac['attr'] = attr
                mac['dbg'] = (q_us, rr, share, d_pkts)
                if int(time.time()) != mac.get('dbg_t', -1):
                    mac['dbg_t'] = int(time.time())
                    print("  MACDBG q=%.0fus rr=%.3f share=%.2f attr=%.2f pkt=%d "
                          "hold=%d/%d"
                          % (q_us, rr, share, attr, d_pkts,
                             mac.get('hold', 0), mac.get('hold2', 0)),
                          flush=True)
                cur = tgt[0] if tgt[0] is not None else cur_rate
                new = cur
                why = ''
                if now - last_change[0] < 0.5:
                    continue
                if q_us > 0.5 * lim:
                    # calibrated 2026-11-06: external contention sits at
                    # share 0.01-0.05, self-congestion at 0.33-0.48, so the
                    # threshold goes in the middle of that gap
                    if share < 0.10:
                        # the air is busy but it is not ours: cutting our rate
                        # would only hurt the picture, the queue is not the
                        # cause.  Keep sending and let FEC/NACK repair.
                        mac['hold'] = mac.get('hold', 0) + 1
                    elif attr < 0.30:
                        # the airtime is charged to our station, but our own
                        # video explains only a small part of it: the backlog
                        # comes from another flow sharing the station.
                        mac['hold2'] = mac.get('hold2', 0) + 1
                    else:
                        new = int(cur * 0.85)
                        why = 'self-congestion q=%.0fus share=%.2f' % (q_us, share)
                elif q_us < 0.20 * lim:
                    # An empty queue means headroom regardless of the retry
                    # rate: on 2.4 GHz the band is busy with neighbours, so
                    # rr sits near 15 even when nothing of ours is queued.
                    new = int(cur * 1.10)
                    why = 'headroom q=%.0fus share=%.2f' % (q_us, share)
                new = max(args.min_rate, min(args.max_rate, new))
                if new != cur and abs(new - cur) > 0.08 * cur:
                    last_change[0] = now
                    tgt[0] = new
                    with sw_lock:
                        switch_req[:] = [new, why]
                    print("  MAC-CTL %.0f -> %.0f kbps (q=%.0fus rr=%.3f "
                          "pkt=%d cost=%.1f share=%.2f)"
                          % (cur / 1000.0, new / 1000.0, q_us, rr, d_pkts, cost, share),
                          flush=True)

        threading.Thread(target=_mac_ctrl, daemon=True).start()

    def _cache_put(sq, blob):
        fcache[sq] = (blob, time.perf_counter())
        if len(fcache) > 4096:
            cutoff = time.perf_counter() - args.cache_ms / 1000.0
            for k in [k for k, v in fcache.items() if v[1] < cutoff]:
                fcache.pop(k, None)

    rtt_hist = []                   # RTCP-style round-trip samples (ms)
    fb_state = {'n': 0, 'dup': 0, 'bad': 0, 'period': 0.0, 'rx_bps': 0.0,
                'loss_pm': 0, 'jit_us': 0, 'q_us': 0, 'maxfid': 0,
                'ok': 0, 'lost': 0, 'seq': -1}
    if args.fb:
        fbrx = txport.FbRx(args.transport, iface=args.fb_iface,
                           port=args.fb_port)
        # Clock-sync responder: the receiver asks for our clock so it can
        # convert its own arrival stamps into real one-way latency.

        def _fb_worker():
            seen, order = set(), collections.deque()
            prev = None
            while True:
                try:
                    item = fbrx.recv_any(0.2)
                except Exception:
                    break
                if item is None:
                    continue
                et, payload, src_mac = item
                if et == rtc2.ETH_CONTROL:
                    continue          # handled by the dedicated sync thread
                try:
                    fb = rtc2.unpack_feedback(payload)
                except Exception:
                    fb_state['bad'] += 1
                    continue
                _ec = fb.get('echo_ts') or 0
                if _ec:
                    _r = ((int(time.perf_counter() * 1e6) & 0xFFFFFFFF) - _ec) & 0xFFFFFFFF
                    if 0 < _r < 1000000:
                        rtt_hist.append(_r / 1000.0)
                s = fb['fb_seq']
                if s in seen:                 # 3x redundancy -> 2 dup per report
                    fb_state['dup'] += 1
                    continue
                seen.add(s)
                order.append(s)
                if len(order) > 512:
                    seen.discard(order.popleft())
                now = time.perf_counter()
                if prev is not None:
                    fb_state['period'] = now - prev
                prev = now
                wu = fb['window_us'] or 1
                fb_state.update(n=fb_state['n'] + 1, seq=s,
                                rx_bps=fb['recv_bytes'] * 8.0 / wu * 1e6,
                                loss_pm=fb['loss_permille'], jit_us=fb['jitter_us'],
                                q_us=fb['q_us'], maxfid=fb['max_frame_id'],
                                ok=fb['frames_ok'], lost=fb['frames_lost'])
                if args.abr:
                    nt = gcc.on_feedback(fb, now)
                    if nt:
                        with sw_lock:
                            switch_req[:] = [nt, gcc.reason]
        threading.Thread(target=_fb_worker, daemon=True).start()
        dbg("feedback listener on %s" % fbrx.desc)

        # Clock-sync responder -- OUR measurement method, and therefore only
        # active on the L2 arm.  The UDP/IP arm stays a plain UDP application:
        # it is not modified, and its latency is measured the conventional way
        # (round-trip time), not with this side channel.
        if args.transport == 'l2':
            sync_tx = txport.FbTx('l2', eth_dev=args.iface,
                                  dst_mac=args.dst, src_mac=args.src,
                                  ethertype=rtc2.ETH_CONTROL)

            def _sync_worker():
                try:
                    crx = txport.CtrlRx('l2', iface=args.fb_iface)
                except Exception as e:
                    dbg("sync responder unavailable: %r" % (e,))
                    return
                while True:
                    item = crx.recv_any(0.2)
                    if item is None:
                        continue
                    payload, src_mac = item
                    # NACK must be tested BEFORE unpack_sync: a NACK payload
                    # has a different magic and would otherwise be dropped.
                    if payload[:4] == rtc2.PLI_MAGIC:
                        force_idr[0] = True
                        pli_rx[0] += 1
                        continue
                    if payload[:4] == rtc2.NACK_MAGIC:
                        try:
                            want = rtc2.unpack_nack(payload)
                        except Exception:
                            continue
                        nowc = time.perf_counter()
                        for s in want:
                            ent = fcache.get(s)
                            if ent is None:
                                continue
                            if nowc - ent[1] > args.cache_ms / 1000.0:
                                continue
                            try:
                                with send_lk:
                                    txp.send(ent[0])
                                resent[0] += 1
                            except Exception:
                                pass
                        continue
                    try:
                        sy = rtc2.unpack_sync(payload)
                    except Exception:
                        continue
                    if sy['magic'] != rtc2.SYNC_REQ:
                        continue
                    t2 = int(time.perf_counter() * 1e6)
                    try:
                        with send_lk:
                            sync_tx.send_to_mac(
                                src_mac,
                                rtc2.pack_sync(rtc2.SYNC_RSP, sy['t_echo'],
                                               t2, t2))
                    except Exception:
                        pass
            threading.Thread(target=_sync_worker, daemon=True).start()

    pacer = Pacer(args.bitrate)
    print("sender: transport=%s | %s | %dx%d@%d %d bps | mtu-chunk=%d"
          % (args.transport, txp.desc, args.width, args.height,
             args.fps, args.bitrate, args.chunk), flush=True)

    seqgen = SeqGen()

    frame_id = 0
    t0 = time.perf_counter()
    t_end = t0 + args.seconds

    # ---- audio ------------------------------------------------------------
    # Shares t0 with the video path on purpose: both streams stamp PTS against
    # the same clock, which is the only way the receiver can align them.
    asrc = None
    audio_stat = {'frames': 0, 'bytes': 0, 'starved': 0, 'rms': 0.0}
    if args.audio != 'off':
        _amode = ('file:' + (args.audio_file or args.video)) if args.audio == 'file' else args.audio
        asrc = AudioSource(_amode,
                           args.audio_rate,
                           dev=(args.audio_dev if args.audio_dev >= 0 else None),
                           gain=args.audio_gain)

        def _audio_loop():
            import numpy as np
            enc = av.CodecContext.create('libopus', 'w')
            enc.sample_rate = args.audio_rate
            enc.layout = 'mono'
            enc.format = 's16'
            enc.bit_rate = int(args.audio_bitrate)
            enc.open()
            samples = 0
            afid = 0
            rms_acc = 0.0
            rms_n = 0
            while time.perf_counter() < t_end:
                blk = asrc.read(0.5)
                if blk is None:
                    audio_stat['starved'] += 1
                    continue
                rms_acc += float((blk.astype(np.float64) ** 2).mean())
                rms_n += 1
                audio_stat['rms'] = (rms_acc / max(rms_n, 1)) ** 0.5
                fr = av.AudioFrame.from_ndarray(
                    blk.reshape(1, -1).astype('int16'), format='s16', layout='mono')
                fr.sample_rate = args.audio_rate
                fr.pts = samples
                fr.time_base = Fraction(1, args.audio_rate)
                try:
                    pkts = enc.encode(fr)
                except Exception as e:
                    print("ERROR audio encode: %r" % (e,), flush=True)
                    samples += blk.shape[0]
                    continue
                samples += blk.shape[0]
                if args.audio_pts == 'samples':
                    pts90 = int(samples * 90000.0 / args.audio_rate)
                else:
                    # The capture device delivers slightly less than realtime
                    # (0.98x here), so a sample-count clock drifts behind the
                    # wall clock and every packet then looks late at playout.
                    pts90 = int((time.perf_counter() - t0) * 90000) & 0x0FFFFFFF
                for p in pkts:
                    data = bytes(p)
                    if not data:
                        continue
                    ts_us = int(time.perf_counter() * 1e6) & 0xFFFFFFFF
                    start = seqgen.reserve(1)
                    chunks, _nx = rtc2.chunk_frame(data, afid, pts90, ts_us, start,
                                                   stream_id=rtc2.S_AUDIO,
                                                   keyframe=True,
                                                   chunk_size=args.chunk)
                    for c in chunks:
                        try:
                            with send_lk:
                                txp.send(c)
                        except Exception:
                            break
                        pacer.wait(len(c) + txp.overhead)
                    audio_stat['frames'] += 1
                    audio_stat['bytes'] += len(data)
                    afid += 1

        threading.Thread(target=_audio_loop, daemon=True).start()
        print("audio: %s %d Hz mono opus %d bps (dev=%s%s)"
              % (args.audio, args.audio_rate, args.audio_bitrate,
                 args.audio_dev if args.audio_dev >= 0 else "default",
                 "  src=" + getattr(asrc, 'src_name', '') if asrc else ""),
              flush=True)
    next_frame_t = t0
    sent_bytes = 0
    sent_chunks = 0
    sent_frames = 0
    keyframes = 0
    send_err = 0
    conv_err = 0
    enc_err = 0
    read_fail = 0
    last_report = t0
    meter = Meter()
    prev_frame_t = t0

    while time.perf_counter() < t_end:
        ta = time.perf_counter()
        ok, img = cap.read()
        tb = time.perf_counter()
        if not ok:
            if args.video:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)      # loop the clip
                ok, img = cap.read()
                tb = time.perf_counter()
            if not ok:
                read_fail += 1
                if read_fail <= 5 or read_fail % 50 == 0:
                    print("WARN read failed (#%d) after %.1f s"
                          % (read_fail, time.perf_counter() - t0), flush=True)
                time.sleep(0.005)
                meter.add('read', tb - ta)
                continue

        now = time.perf_counter()
        # Frame timeline, not wall clock: with the audio stream anchored to
        # its sample count, a wall-clock video timeline drifts away from it
        # whenever a frame takes longer than 1/fps.  Deriving pts from the
        # frame index keeps both timelines tied to the file, so the A/V
        # relationship is exact by construction.
        pts = int(frame_id * 90000.0 / max(args.fps, 1))
        try:
            vf = av.VideoFrame.from_ndarray(img, format='bgr24').reformat(format='yuv420p')
        except Exception as e:
            conv_err += 1
            print("ERROR convert frame %d: %r" % (frame_id, e), flush=True)
            continue
        tc2 = time.perf_counter()

        if switch_req:
            with sw_lock:
                nt, why = switch_req[0], switch_req[1]
                del switch_req[:]
            old_rate, cur_rate = cur_rate, nt
            tsw = time.perf_counter()
            try:
                enc.close()
            except Exception:
                pass
            enc = build_encoder(args.width, args.height, args.fps, nt)
            pacer.set_rate(nt)
            abr_log.append((time.perf_counter() - t0, nt, why))
            print("  ABR %.0f -> %.0f kbps (%s)  reopen %.1f ms + IDR"
                  % (old_rate / 1000.0, nt / 1000.0, why,
                     (time.perf_counter() - tsw) * 1000), flush=True)

        vf.pts = frame_id
        vf.time_base = Fraction(1, args.fps)
        try:
            if force_idr[0]:
                # PLI: the peer lost a whole frame, so the reference chain is
                # broken -- encode this one as an IDR instead of waiting for
                # the periodic one.
                try:
                    vf.pict_type = 'I'
                    force_idr[0] = False
                except Exception:
                    pass
            packets = enc.encode(vf)
        except Exception as e:
            enc_err += 1
            print("ERROR encode frame %d: %r" % (frame_id, e), flush=True)
            continue
        td = time.perf_counter()

        frame_bytes = 0
        frame_chunks = 0
        seq_first = -1
        last_kf = False
        for pkt in packets:
            data = bytes(pkt)
            if not data:
                continue
            kf = is_key(pkt)
            if kf:
                keyframes += 1
            ts_us = int(time.perf_counter() * 1e6) & 0xFFFFFFFF
            nch = max(1, (len(data) + args.chunk - 1) // args.chunk)
            seq = seqgen.reserve(nch)
            if seq_first < 0:
                seq_first = seq
            last_kf = last_kf or kf
            # one encoded packet == one RTC frame, so the id must be unique
            # per packet: a video frame can emit several packets and reusing
            # frame_id made the receiver merge them into bogus frames
            pkt_id[0] += 1
            chunks, _nx = rtc2.chunk_frame(data, pkt_id[0], pts, ts_us, seq,
                                           stream_id=rtc2.S_VIDEO, keyframe=kf,
                                           chunk_size=args.chunk)
            tck = time.perf_counter()
            for ci, c in enumerate(chunks):
                tsn = time.perf_counter()
                try:
                    with send_lk:
                        txp.send(c)
                except Exception as e:
                    send_err += 1
                    if send_err <= 5:
                        print("ERROR send chunk %d of frame %d: %r"
                              % (c and 0, frame_id, e), flush=True)
                    break
                tpn = time.perf_counter()
                sent_bytes += len(c) + txp.overhead
                sent_chunks += 1
                frame_bytes += len(c)
                frame_chunks += 1
                _cache_put(seq + ci, c)
                meter.add('send', tpn - tsn)
                pacer.wait(len(c) + txp.overhead)
                meter.add('pace', time.perf_counter() - tpn)

            if args.fec and frame_chunks == len(chunks) and chunks:
                try:
                    par = rtc2.make_parity(chunks, pkt_id[0], pts, ts_us,
                                           seq + len(chunks))
                    with send_lk:
                        txp.send(par)
                    _cache_put(seq + len(chunks), par)
                    sent_bytes += len(par) + txp.overhead
                    sent_chunks += 1
                    fec_sent[0] += 1
                except Exception as e:
                    if fec_err[0] < 3:
                        fec_err[0] += 1
                        print("WARN parity: %r" % (e,), flush=True)
            meter.add('chunk', tck - td)
            sent_frames += 1

        meter.add('read', tb - ta)
        meter.add('conv', tc2 - tb)
        meter.add('enc', td - tc2)
        meter.bump()

        if V:
            gap_ms = (ta - prev_frame_t) * 1000.0
            prev_frame_t = ta
            dbg("  f=%-4d kf=%d enc=%5.1fms in=%5d B out=%4d B chunks=%2d "
                "seq=%d..%d gap=%5.1fms lat_tx=%5.1fms"
                % (frame_id, 1 if last_kf else 0,
                   (td - tc2) * 1000.0, len(img.tobytes()),
                   frame_bytes, frame_chunks, max(seq_first, 0),
                   max(seq_first, 0) + frame_chunks - 1 if frame_chunks else 0,
                   gap_ms, (time.perf_counter() - ta) * 1000.0))

        frame_id += 1
        next_frame_t += 1.0 / args.fps
        tr = time.perf_counter()
        d = next_frame_t - tr
        if d > 0:
            time.sleep(d)
        else:
            next_frame_t = time.perf_counter()
        meter.add('tail', time.perf_counter() - tr)

        if time.perf_counter() - last_report >= 1.0:
            el = time.perf_counter() - t0
            print("  t=%4.1fs frames=%d chunks=%d kf=%d  tx=%.2f Mbps  fps=%.1f"
                  % (el, sent_frames, sent_chunks, keyframes,
                     sent_bytes * 8 / el / 1e6, sent_frames / el), flush=True)
            if fbrx:
                print("    fb #%d n=%d dup=%d per=%.0fms rx=%.2fMbps loss=%d/1000 "
                      "jit=%.1fms q=%.0fms maxfid=%d ok=%d lost=%d"
                      % (fb_state['seq'], fb_state['n'], fb_state['dup'],
                         fb_state['period'] * 1000, fb_state['rx_bps'] / 1e6,
                         fb_state['loss_pm'], fb_state['jit_us'] / 1000.0,
                         fb_state['q_us'] / 1000.0, fb_state['maxfid'],
                         fb_state['ok'], fb_state['lost']), flush=True)
            if asrc:
                print("    audio %d frames %dB rms=%.1f%s"
                      % (audio_stat['frames'], audio_stat['bytes'],
                         audio_stat['rms'],
                         "" if audio_stat['starved'] == 0
                         else "  starved=%d" % audio_stat['starved']), flush=True)
            if args.abr:
                print("    abr %.0f kbps  last=%s  jit=%.1f base=%.1f  switches=%d"
                      % (cur_rate / 1000.0, gcc.reason, gcc.jit or 0.0, gcc.base or 0.0,
                         len(abr_log)), flush=True)
            if V:
                print("    stages: " + meter.line(), flush=True)
                print("    errors: read=%d conv=%d enc=%d send=%d  pacer_slept=%.1fms/frame"
                      % (read_fail, conv_err, enc_err, send_err,
                         pacer.slept / max(meter.n, 1) * 1000), flush=True)
                meter.reset()
            last_report = time.perf_counter()

    el = time.perf_counter() - t0
    print("done: %d frames, %d chunks, %d keyframes, %.2f Mbps avg, %.1f fps"
          % (sent_frames, sent_chunks, keyframes,
             sent_bytes * 8 / el / 1e6, sent_frames / el), flush=True)
    if read_fail or conv_err or enc_err or send_err:
        print("errors: read=%d conv=%d enc=%d send=%d"
              % (read_fail, conv_err, enc_err, send_err), flush=True)
    if asrc:
        print("audio: %d frames, %d bytes payload, rms=%.1f, starved=%d"
              % (audio_stat['frames'], audio_stat['bytes'],
                 audio_stat['rms'], audio_stat['starved']), flush=True)
        asrc.close()

    if args.mac_ctl:
        print("mac: %d reports, last(aql_vo,aql_be,tx_us,rx_us,retries,failed)=%s"
              % (mac['rx'], mac['last']), flush=True)
    if args.fec:
        print("pli: %d keyframe requests received" % pli_rx[0], flush=True)
        print("fec: %d parity chunks sent, %d resent on NACK, %d errors"
              % (fec_sent[0], resent[0], fec_err[0]), flush=True)
    if fbrx:
        print("feedback: %d reports, %d duplicates dropped, %d malformed, last rx=%.2f Mbps "
              "loss=%d/1000 jitter=%.1f ms queue=%.0f ms peer_maxfid=%d"
              % (fb_state['n'], fb_state['dup'], fb_state['bad'],
                 fb_state['rx_bps'] / 1e6, fb_state['loss_pm'],
                 fb_state['jit_us'] / 1000.0, fb_state['q_us'] / 1000.0,
                 fb_state['maxfid']), flush=True)
        if rtt_hist:
            _s = sorted(rtt_hist)

            def _p(v, p):
                return v[min(len(v) - 1, int(len(v) * p / 100.0))]

            print("rtt (RTCP-style, same for both arms): p50=%.1f p95=%.1f "
                  "min=%.1f max=%.1f ms (n=%d)"
                  % (_p(_s, 50), _p(_s, 95), _s[0], _s[-1], len(_s)), flush=True)
        fbrx.close()

    if args.abr:
        print("abr: %d switches (%d up, %d down), final %.0f kbps"
              % (len(abr_log), gcc.n_up, gcc.n_down, cur_rate / 1000.0), flush=True)
        for _t, _r, _w in abr_log:
            print("   t=%5.2fs -> %6.0f kbps  %s" % (_t, _r / 1000.0, _w), flush=True)

    cap.release(); txp.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
