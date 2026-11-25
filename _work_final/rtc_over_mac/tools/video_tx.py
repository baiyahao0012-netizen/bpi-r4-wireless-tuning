#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pi-side video sender: paced JPEG frames over L2 + questions bound to frames.

At the frame whose interval covers question time t, the question is sent right
after that frame's last fragment. Answers come back on 0x88B6 (A01) and the
first byte is t3 for the end-to-end metric.
"""
import argparse
import glob
import json
import os
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_proto import (ETH_QA, ETH_VIDEO, FRAME_MAX, VID_PAYLOAD, VI,
                         ack, answer, mac, parse, question, video_frag)


class Sender:
    def __init__(self, a):
        self.a = a
        self.src = mac(a.src_mac)
        self.dst = mac(a.dst_mac)
        self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                                  socket.htons(0x0003))
        self.sock.bind((a.iface, 0))
        self.sock.settimeout(0.05)          # RX only: answers
        self.tx = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                                socket.htons(0x0003))
        self.tx.bind((a.iface, 0))
        self.tx.settimeout(None)            # TX must block, not raise
        self.stop = False
        self.lock = threading.RLock()
        self.frames = sorted(glob.glob(os.path.join(a.frames, "*.jpg")))
        self.questions = []
        with open(a.questions, "r", encoding="utf-8-sig") as fh:
            head = fh.readline()
            for line in fh:
                parts = line.strip().split(",", 3)
                if len(parts) < 3:
                    continue
                try:
                    t = float(parts[0])
                except ValueError:
                    continue
                q = parts[2].strip().strip('"')
                self.questions.append((t, q))
        self.by_frame = {}
        for t, q in self.questions:
            self.by_frame[int(round(t * a.fps)) + 1] = (t, q)
        self.qid = 0
        self.pending = {}       # qid -> t0_ns
        self.e2e_us = []
        self.answers = {}
        self.frames_sent = 0
        self.frags_sent = 0
        self.late = 0
        self.questions_sent = 0
        self.acks_sent = 0
        self.ack_max = {}
        self.ack_last = {}
        self.preload = {}
        if a.preload:
            for p in self.frames:
                with open(p, "rb") as fh:
                    self.preload[os.path.basename(p)] = fh.read()

    def jpeg(self, path):
        if self.preload:
            return self.preload[os.path.basename(path)]
        with open(path, "rb") as fh:
            return fh.read()

    def rx_loop(self):
        while not self.stop:
            try:
                raw = self.sock.recv(65535)
            except socket.timeout:
                continue
            p = parse(raw)
            if not p or p["type"] != "answer":
                continue
            qid = p["qid"]
            with self.lock:
                self.ack_max[qid] = max(self.ack_max.get(qid, -1), p["seq"])
            now = time.monotonic_ns()
            with self.lock:
                t0 = self.pending.get(qid)
                if t0 is not None and (p["flags"] & 1) and "first" not in self.answers.get(qid, {}):
                    self.answers.setdefault(qid, {})["first"] = now
                    self.e2e_us.append((now - t0) / 1000.0)
                rec = self.answers.setdefault(qid, {})
                rec["text"] = rec.get("text", "") + p["text"]
                if p["flags"] & 2:
                    rec["done"] = now
            if p["flags"] & 1:
                self.log("first_answer", qid, "")

    def log(self, ev, qid, detail=""):
        if self.a.csv:
            with self.lock, open(self.a.csv, "a", buffering=1) as fh:
                fh.write("%d,%s,%d,%s\n" % (time.monotonic_ns(), ev, qid, detail))

    def send_question(self, qid, idx, pts_us, t0_ns, text):
        frame = question(self.dst, self.src, qid, idx, pts_us, t0_ns, text)
        self.tx.send(frame)
        with self.lock:
            self.pending[qid] = t0_ns
            self.questions_sent += 1
        self.log("question", qid, "idx=%d" % idx)

    def ack_loop(self):
        while not self.stop:
            with self.lock:
                pending = [(q, s) for q, s in self.ack_max.items()
                           if self.ack_last.get(q) != s]
            for q, s in pending:
                try:
                    for _ in range(3):
                        self.tx.send(ack(self.dst, self.src, q, s))
                        with self.lock:
                            self.acks_sent += 1
                        time.sleep(0.002)
                    with self.lock:
                        self.ack_last[q] = s
                except OSError:
                    pass
            time.sleep(0.02)

    def run(self):
        th = threading.Thread(target=self.rx_loop, daemon=True)
        th.start()
        threading.Thread(target=self.ack_loop, daemon=True).start()
        n = len(self.frames)
        if n == 0:
            raise SystemExit("no frames in %s" % self.a.frames)
        total = n * self.a.loop
        t_start = time.monotonic()
        t_end = t_start + self.a.seconds if self.a.seconds > 0 else None
        sent = 0
        for k in range(total):
            if self.stop:
                break
            if t_end is not None and time.monotonic() >= t_end:
                break
            loop_i, k_in = divmod(k, n)
            idx = k_in + 1
            pts_us = int(k_in * 1e6 / self.a.fps)
            target = t_start + k / self.a.fps
            now = time.monotonic()
            if now < target:
                time.sleep(target - now)
            elif now - target > 0.2:
                self.late += 1
            data = self.jpeg(self.frames[k_in])
            nfrag = (len(data) + VID_PAYLOAD - 1) // VID_PAYLOAD
            if nfrag > 65535:
                raise SystemExit("frame too large: %d" % len(data))
            for fi in range(nfrag):
                chunk = data[fi * VID_PAYLOAD:(fi + 1) * VID_PAYLOAD]
                self.tx.send(video_frag(self.dst, self.src, idx, pts_us, fi,
                                        nfrag, chunk))
                self.frags_sent += 1
            self.frames_sent += 1
            sent += 1
            qidx = idx if idx in self.by_frame else None
            if qidx is None and (loop_i * n + idx) == total:
                # last frame: allow a question mapped one past the end
                cand = idx + 1
                if cand in self.by_frame and loop_i == self.a.loop - 1:
                    qidx = cand
            if qidx is not None:
                t_q, text = self.by_frame[qidx]
                self.qid += 1
                qid = loop_i * 100000 + self.qid
                self.send_question(qid, idx, pts_us, time.monotonic_ns(), text)
        # wait for in-flight answers before shutting the RX thread down
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            with self.lock:
                done = len(self.e2e_us)
            if done >= self.questions_sent:
                break
            time.sleep(0.05)
        self.stop = True
        time.sleep(0.2)
        e2e = sorted(self.e2e_us)
        res = {"role": "pi-video-tx", "fps": self.a.fps, "frames": n,
               "loops": self.a.loop, "frames_sent": self.frames_sent,
               "frags_sent": self.frags_sent, "late_frames": self.late,
               "questions_sent": self.questions_sent,
               "acks_sent": self.acks_sent,
               "answers_first": len(self.e2e_us),
               "e2e_p50_us": round(e2e[len(e2e) // 2], 1) if e2e else None,
               "e2e_p95_us": round(e2e[int(len(e2e) * 0.95)], 1) if e2e else None,
               "e2e_us": [round(x, 1) for x in e2e]}
        if self.a.out:
            with open(self.a.out, "w", encoding="utf-8") as fh:
                json.dump(res, fh, ensure_ascii=False)
        print("RESULT " + json.dumps(res, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", default="wlan0")
    ap.add_argument("--src-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--dst-mac", default="40:c2:ba:52:70:95")
    ap.add_argument("--frames", default="/tmp/vframes")
    ap.add_argument("--questions", default="/tmp/questions.csv")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--loop", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=0)
    ap.add_argument("--preload", action="store_true")
    ap.add_argument("--csv", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    Sender(a).run()


if __name__ == "__main__":
    main()






