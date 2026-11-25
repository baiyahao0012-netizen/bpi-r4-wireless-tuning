#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI client (Pi): request generator + feedback loop + TTFT measurement.

The server (laptop behind the AP) owns the downlink scheduler; this side only
sends requests and measures the response time, so TTFT reflects the AP egress
queue where the bulk traffic competes.
"""
import argparse
import json
import os
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import (ETH_AI, ETH_ACK, ETH_BULK, KIND_REQ,
                          build_frame, parse_frame, mac_bytes)


class Client:
    def __init__(self, a):
        self.a = a
        self.src = mac_bytes(a.src_mac)
        self.dst = mac_bytes(a.dst_mac)
        self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                                  socket.htons(0x0003))
        self.sock.bind((a.iface, 0))
        self.sock.settimeout(0.05)
        self.lock = threading.RLock()
        self.stop = False
        self.outstanding = {}   # request awaiting server ACK
        self.awaiting = {}      # request awaiting response (TTFT start point)
        self.ttft_us = []
        self.stats = {"requests": 0, "delivered": 0, "resends": 0,
                      "resp_timeout_resend": 0, "bulk_rx": 0, "acks_rx": 0}
        self.csv = open(a.csv, "w", buffering=1) if a.csv else None
        if self.csv:
            self.csv.write("t_ns,event,msg_id,detail\n")

    def log(self, event, msg_id, detail=""):
        with self.lock:
            if self.csv:
                self.csv.write("%d,%s,%d,%s\n" %
                               (time.monotonic_ns(), event, msg_id, detail))

    def send_req(self, mid, t0_ns):
        frame = build_frame(self.dst, self.src, ETH_AI, 0, mid, KIND_REQ,
                            t0_ns, b"Q%08d" % (mid & 0xFFFFFFF))
        self.sock.send(frame)
        self.log("tx_req", mid, "")

    def rx_loop(self):
        while not self.stop:
            try:
                raw = self.sock.recv(65535)
            except socket.timeout:
                continue
            p = parse_frame(raw)
            if not p or p["src"] == self.src:
                continue
            if p["ethertype"] == ETH_BULK:
                self.stats["bulk_rx"] += 1
                continue
            if p["ethertype"] == ETH_ACK:
                with self.lock:
                    self.outstanding.pop(p["msg_id"], None)
                self.stats["acks_rx"] += 1
                continue
            if p["ethertype"] == ETH_AI and p["kind"] == 1:
                mid = p["msg_id"]
                with self.lock:
                    rec = self.awaiting.pop(mid, None)
                if rec is not None:
                    self.ttft_us.append((time.monotonic_ns() - rec["t0_ns"]) / 1000.0)
                    self.stats["delivered"] += 1
                    self.log("ttft", mid, "%.1f" % self.ttft_us[-1])
                # ack the response so the server can retire it
                self.sock.send(build_frame(self.dst, self.src, ETH_ACK, 0, mid,
                                           3, 0, struct.pack("!I", 0)))

    def gen_loop(self):
        t_end = time.monotonic() + self.a.seconds
        mid = self.a.msg_base
        next_t = time.monotonic()
        while time.monotonic() < t_end and not self.stop:
            now = time.monotonic()
            if now < next_t:
                time.sleep(0.001)
                continue
            t0 = time.monotonic_ns()
            try:
                self.send_req(mid, t0)
            except OSError as exc:
                self.log("send_err", mid, str(exc))
                continue
            with self.lock:
                self.outstanding[mid] = {"t0_ns": t0, "attempts": 1,
                                         "last_ns": time.monotonic_ns()}
                self.awaiting[mid] = {"t0_ns": t0, "last_ns": time.monotonic_ns(),
                                      "attempts": 0}
                self.stats["requests"] += 1
            mid += 1
            next_t += self.a.ai_interval_ms / 1000.0

    def retx_loop(self):
        while not self.stop:
            now = time.monotonic_ns()
            to_resend = []
            with self.lock:
                for mid, rec in list(self.outstanding.items()):
                    if rec["attempts"] > self.a.max_resend:
                        continue
                    if (now - rec["last_ns"]) / 1e6 >= self.a.ack_timeout_ms:
                        rec["attempts"] += 1
                        rec["last_ns"] = now
                        to_resend.append((mid, rec["t0_ns"]))
            for mid, t0 in to_resend:
                try:
                    self.send_req(mid, t0)
                    self.stats["resends"] += 1
                    self.log("resend", mid, "")
                except OSError:
                    pass
            # responses that never arrived -> resend the request (safety net)
            now = time.monotonic_ns()
            resp_retry = []
            with self.lock:
                for mid, rec in list(self.awaiting.items()):
                    if mid not in self.outstanding:
                        continue  # request already ACKed: server owns the response retx
                    if rec["attempts"] >= self.a.max_resend:
                        continue
                    if (now - rec["last_ns"]) / 1e6 >= self.a.resp_timeout_ms * (2 ** min(rec["attempts"], 3)):
                        rec["attempts"] += 1
                        rec["last_ns"] = now
                        resp_retry.append((mid, rec["t0_ns"]))
            for mid, t0 in resp_retry:
                try:
                    self.send_req(mid, t0)
                    self.stats["resp_timeout_resend"] += 1
                    self.log("resp_timeout_resend", mid, "")
                except OSError:
                    pass
            time.sleep(0.01)

    def run(self):
        ts = [threading.Thread(target=f, daemon=True)
              for f in (self.rx_loop, self.gen_loop, self.retx_loop)]
        for t in ts:
            t.start()
        time.sleep(self.a.seconds)
        self.stop = True
        time.sleep(0.3)
        return self.summary()

    def summary(self):
        tt = sorted(self.ttft_us)

        def pct(q):
            return round(tt[min(len(tt) - 1, int(len(tt) * q))], 1) if tt else None

        r = {"role": "client", "mode": self.a.mode}
        r.update(self.stats)
        r["delivery_ratio"] = round(self.stats["delivered"] /
                                    max(1, self.stats["requests"]), 4)
        r["ttft_p50_us"] = pct(0.5)
        r["ttft_p95_us"] = pct(0.95)
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="client")
    ap.add_argument("--iface", default="wlan1")
    ap.add_argument("--src-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--dst-mac", required=True)
    ap.add_argument("--seconds", type=float, default=12)
    ap.add_argument("--ai-interval-ms", type=float, default=100.0)
    ap.add_argument("--ack-timeout-ms", type=float, default=60.0)
    ap.add_argument("--resp-timeout-ms", type=float, default=120.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--msg-base", type=int, default=0)
    ap.add_argument("--csv", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = Client(a).run()
    text = "RESULT " + json.dumps(res, ensure_ascii=False)
    print(text, flush=True)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()



