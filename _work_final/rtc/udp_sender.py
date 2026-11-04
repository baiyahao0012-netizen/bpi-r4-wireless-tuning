# -*- coding: utf-8 -*-
"""Baseline B: the traditional transport chain -- same framing and encoder as
the RTC sender, but carried in UDP/IP datagrams with no jitter buffer, no
feedback and no rate control.  This is what a naive UDP video pipeline gives.
"""
import argparse, time, sys, cv2, av, socket
from fractions import Fraction
import rtc2


class Pacer(object):
    def __init__(self, bps):
        self.bps = float(bps) * 1.3
        self.t0 = time.perf_counter()
        self.sent = 0
        self.slept = 0.0

    def wait(self, nbytes):
        self.sent += nbytes
        ideal = self.t0 + self.sent * 8.0 / self.bps
        d = ideal - time.perf_counter()
        if d > 0.001:
            time.sleep(d)
            self.slept += d


def build_encoder(w, h, fps, bitrate):
    c = av.CodecContext.create('libx264', 'w')
    c.width, c.height = w, h
    c.pix_fmt = 'yuv420p'
    c.time_base = Fraction(1, fps)
    c.framerate = Fraction(fps, 1)
    c.bit_rate = int(bitrate)
    c.gop_size = max(2, fps * 2)
    c.max_b_frames = 0
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
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seconds', type=float, default=9)
    ap.add_argument('--bitrate', type=int, default=2500000)
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--height', type=int, default=480)
    ap.add_argument('--dst-ip', default='192.168.240.147')
    ap.add_argument('--dst-port', type=int, default=9911)
    ap.add_argument('--src-ip', default='192.168.240.2')
    ap.add_argument('--chunk', type=int, default=rtc2.DEFAULT_CHUNK)
    ap.add_argument('--verbose', '-v', action='store_true')
    args = ap.parse_args()

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, args.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        print("ERROR camera", flush=True)
        return 2

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.src_ip, 0))
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 << 20)
    except Exception:
        pass
    dst = (args.dst_ip, args.dst_port)
    print("udp sender %s:0 -> %s:%d | %dx%d@%d %d bps | chunk=%d"
          % (args.src_ip, args.dst_ip, args.dst_port, args.width, args.height,
             args.fps, args.bitrate, args.chunk), flush=True)

    enc = build_encoder(args.width, args.height, args.fps, args.bitrate)
    pacer = Pacer(args.bitrate)
    t0 = time.perf_counter()
    t_end = t0 + args.seconds
    frame_id = seq = 0
    sent_frames = sent_chunks = sent_bytes = keyframes = send_err = 0
    last_report = t0
    prev_t = t0

    while time.perf_counter() < t_end:
        ta = time.perf_counter()
        ok, img = cap.read()
        if not ok:
            time.sleep(0.005)
            continue
        now = time.perf_counter()
        pts = int((now - t0) * 90000)
        vf = av.VideoFrame.from_ndarray(img, format='bgr24').reformat(format='yuv420p')
        vf.pts = frame_id
        vf.time_base = Fraction(1, args.fps)
        try:
            packets = enc.encode(vf)
        except Exception as e:
            print("ERROR encode: %r" % (e,), flush=True)
            continue
        fbytes = fchunks = 0
        for pkt in packets:
            data = bytes(pkt)
            if not data:
                continue
            if is_key(pkt):
                keyframes += 1
            ts_us = int(time.perf_counter() * 1e6) & 0xFFFFFFFF
            chunks, seq = rtc2.chunk_frame(data, frame_id, pts, ts_us, seq,
                                           stream_id=rtc2.S_VIDEO,
                                           keyframe=is_key(pkt),
                                           chunk_size=args.chunk)
            for c in chunks:
                try:
                    sock.sendto(c, dst)
                except Exception as e:
                    send_err += 1
                    if send_err <= 5:
                        print("ERROR send: %r" % (e,), flush=True)
                    break
                sent_bytes += len(c)
                sent_chunks += 1
                fbytes += len(c)
                fchunks += 1
                pacer.wait(len(c) + 28)
            sent_frames += 1
        frame_id += 1
        if args.verbose:
            print("  f=%-4d out=%4d B chunks=%2d gap=%5.1fms"
                  % (frame_id - 1, fbytes, fchunks, (ta - prev_t) * 1000), flush=True)
        prev_t = ta
        if now - last_report >= 1.0:
            el = now - t0
            print("  t=%4.1fs frames=%d chunks=%d kf=%d tx=%.2f Mbps fps=%.1f"
                  % (el, sent_frames, sent_chunks, keyframes,
                     sent_bytes * 8 / max(el, .001) / 1e6, sent_frames / max(el, .001)),
                  flush=True)
            last_report = now
        nxt = ta + 1.0 / args.fps
        d = nxt - time.perf_counter()
        if d > 0:
            time.sleep(d)

    el = time.perf_counter() - t0
    cap.release(); sock.close()
    print("done: %d frames, %d chunks, %d keyframes, %.2f Mbps avg, %.1f fps, "
          "send_err=%d" % (sent_frames, sent_chunks, keyframes,
                           sent_bytes * 8 / max(el, .001) / 1e6,
                           sent_frames / max(el, .001), send_err), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
