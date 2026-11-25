#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI client: request generator + feedback state machine + ledger + echo probe.

Records per message: t0, attempts, resend reasons, ttft, dup_resp,
resp_from_attempt (read from the response's flags field).

Injection (process-local, deterministic):
  --drop-req mid:n    first n request sends of mid are pretended-lost
  --fail-req mid:n    first n request sends fail immediately (event path)
  --drop-ack-resp mid:n  suppress the first n response ACKs for mid
"""
import argparse
import collections
import json
import os
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import (ETH_AI, ETH_ACK, ETH_BULK, ETH_ECHO, KIND_REQ,
                          build_frame, parse_frame, mac_bytes)


def parse_spec(s):
    out = {}
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        mid, n = part.split(":")
        out[int(mid)] = int(n)
    return out


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
        self.outstanding = {}
        self.awaiting = {}
        self.records = {}
        self.done_mids = set()
        self.echo = {}
        self.echo_rtt_us = []
        self.inject_drop = parse_spec(a.drop_req)
        self.inject_fail = parse_spec(a.fail_req)
        self.drop_ack_resp = parse_spec(a.drop_ack_resp)
        self.ack_sent = collections.Counter()
        self.stats = {"requests": 0, "delivered": 0, "resends": 0,
                      "resp_timeout_resend": 0, "injected_drop": 0,
                      "injected_fail": 0, "dup_resp": 0, "acks_rx": 0,
                      "bulk_rx": 0, "echo_sent": 0, "echo_rx": 0}
        self.csv = open(a.csv, "w", buffering=1) if a.csv else None
        if self.csv:
            self.csv.write("t_ns,event,msg_id,detail\n")

    def log(self, event, mid, detail=""):
        with self.lock:
            if self.csv:
                self.csv.write("%d,%s,%d,%s\n" %
                               (time.monotonic_ns(), event, mid, detail))

    def _rec(self, mid, t0):
        r = self.records.get(mid)
        if r is None:
            r = {"mid": mid, "t0_ns": t0, "attempts": 0, "reasons": [],
                 "t_resp_ns": 0, "ttft_us": None, "dup_resp": 0,
                 "resp_from_attempt": None, "done": False}
            self.records[mid] = r
        return r

    def send_req(self, mid, t0_ns, reason=None):
        with self.lock:
            rec = self._rec(mid, t0_ns)
            n = rec["attempts"] + 1
            if self.inject_drop.get(mid, 0) >= n:
                self.stats["injected_drop"] += 1
                rec["attempts"] = n
                if reason:
                    rec["reasons"].append(reason)
                self.outstanding[mid] = {"last_ns": time.monotonic_ns(),
                                         "attempts": rec["attempts"]}
                self.log("inject_drop_req", mid, "n=%d" % n)
                return
            if self.inject_fail.get(mid, 0) >= n:
                self.stats["injected_fail"] += 1
                rec["attempts"] = n
                self.log("inject_fail_req", mid, "n=%d" % n)
                # event path: retry immediately (no timeout wait)
                self.send_req(mid, t0_ns, reason="send_fail")
                return
        frame = build_frame(self.dst, self.src, ETH_AI, 0, mid, KIND_REQ,
                            t0_ns, b"Q%08d" % (mid & 0xFFFFFFF))
        self.sock.send(frame)
        with self.lock:
            rec["attempts"] = n
            if reason:
                rec["reasons"].append(reason)
            self.outstanding[mid] = {"last_ns": time.monotonic_ns(),
                                     "attempts": rec["attempts"]}
            self.log("tx_req", mid, "attempt=%d" % n)

    # ---------- RX ----------
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
            if p["ethertype"] == ETH_ECHO:
                mid = p["msg_id"]
                now = time.monotonic_ns()
                with self.lock:
                    t0 = self.echo.pop(mid, None)
                if t0 is not None:
                    self.echo_rtt_us.append((now - t0) / 1000.0)
                    self.stats["echo_rx"] += 1
                continue
            if p["ethertype"] == ETH_ACK:
                with self.lock:
                    self.outstanding.pop(p["msg_id"], None)
                self.stats["acks_rx"] += 1
                continue
            if p["ethertype"] == ETH_AI and p["kind"] == 1:
                mid = p["msg_id"]
                now = time.monotonic_ns()
                with self.lock:
                    rec = self.records.get(mid)
                    dup = mid in self.done_mids
                    if dup:
                        self.stats["dup_resp"] += 1
                        if rec is not None:
                            rec["dup_resp"] += 1
                    else:
                        aw = self.awaiting.pop(mid, None)
                        if aw is not None and rec is not None:
                            rec["t_resp_ns"] = now
                            rec["ttft_us"] = (now - rec["t0_ns"]) / 1000.0
                            rec["resp_from_attempt"] = p["flags"] or None
                            rec["done"] = True
                            self.done_mids.add(mid)
                            self.stats["delivered"] += 1
                            self.log("ttft", mid, "%.1f" % rec["ttft_us"])
                    n_ack = self.ack_sent[mid] + 1
                    send_ack = self.drop_ack_resp.get(mid, 0) < n_ack
                    if send_ack:
                        self.ack_sent[mid] = n_ack
                if send_ack:
                    try:
                        self.sock.send(build_frame(self.dst, self.src, ETH_ACK, 0,
                                                   mid, 3, 0, struct.pack("!I", 0)))
                    except OSError:
                        pass

    # ---------- TX ----------
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
                self.stats["requests"] += 1
                self.awaiting[mid] = {"t0_ns": t0, "last_ns": time.monotonic_ns(),
                                      "attempts": 0}
            mid += 1
            next_t += self.a.ai_interval_ms / 1000.0

    # ---------- echo ----------
    def echo_loop(self):
        n = 0
        while not self.stop and n < self.a.echo:
            mid = 900000 + n
            t0 = time.monotonic_ns()
            with self.lock:
                self.echo[mid] = t0
            try:
                self.sock.send(build_frame(self.dst, self.src, ETH_ECHO, 0, mid,
                                           0, t0, b"E%07d" % n))
                self.stats["echo_sent"] += 1
            except OSError:
                pass
            n += 1
            time.sleep(0.05)

    # ---------- retransmit ----------
    def retx_loop(self):
        while not self.stop:
            now = time.monotonic_ns()
            req_retry = []
            with self.lock:
                for mid, o in list(self.outstanding.items()):
                    rec = self.records.get(mid)
                    if rec is None or rec["attempts"] > self.a.max_resend:
                        continue
                    if (now - o["last_ns"]) / 1e6 >= self.a.ack_timeout_ms * (2 ** min(rec["attempts"] - 1, 3)):
                        req_retry.append((mid, rec["t0_ns"]))
            for mid, t0 in req_retry:
                try:
                    self.send_req(mid, t0, reason="ack_timeout")
                    self.stats["resends"] += 1
                except OSError:
                    pass
            now = time.monotonic_ns()
            resp_retry = []
            with self.lock:
                for mid, aw in list(self.awaiting.items()):
                    if mid not in self.outstanding:
                        continue
                    if aw["attempts"] >= self.a.max_resend:
                        continue
                    if (now - aw["last_ns"]) / 1e6 >= self.a.resp_timeout_ms * (2 ** min(aw["attempts"], 3)):
                        aw["attempts"] += 1
                        aw["last_ns"] = now
                        resp_retry.append((mid, aw["t0_ns"]))
            for mid, t0 in resp_retry:
                try:
                    self.send_req(mid, t0, reason="resp_timeout")
                    self.stats["resp_timeout_resend"] += 1
                except OSError:
                    pass
            time.sleep(0.01)

    def run(self):
        ts = [threading.Thread(target=f, daemon=True)
              for f in (self.rx_loop, self.gen_loop, self.echo_loop, self.retx_loop)]
        for t in ts:
            t.start()
        time.sleep(self.a.seconds)
        self.stop = True
        time.sleep(0.3)
        res = {"role": "client", "requests": self.stats["requests"],
               "delivered": self.stats["delivered"],
               "delivery_ratio": round(self.stats["delivered"] / max(1, self.stats["requests"]), 4)}
        res.update(self.stats)
        rtt = sorted(self.echo_rtt_us)
        res["echo_p50_us"] = round(rtt[len(rtt)//2], 1) if rtt else None
        res["echo_p95_us"] = round(rtt[int(len(rtt)*0.95)], 1) if rtt else None
        tts = sorted(r["ttft_us"] for r in self.records.values() if r["ttft_us"] is not None)
        res["ttft_p50_us"] = round(tts[len(tts)//2], 1) if tts else None
        res["ttft_p95_us"] = round(tts[int(len(tts)*0.95)], 1) if tts else None
        if self.a.ledger:
            with open(self.a.ledger, "w", encoding="utf-8") as fh:
                for mid, r in self.records.items():
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iface", default="wlan0")
    ap.add_argument("--src-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--dst-mac", required=True)
    ap.add_argument("--seconds", type=float, default=12)
    ap.add_argument("--ai-interval-ms", type=float, default=100.0)
    ap.add_argument("--ack-timeout-ms", type=float, default=60.0)
    ap.add_argument("--resp-timeout-ms", type=float, default=120.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--msg-base", type=int, default=0)
    ap.add_argument("--echo", type=int, default=0)
    ap.add_argument("--drop-req", default="")
    ap.add_argument("--fail-req", default="")
    ap.add_argument("--drop-ack-resp", default="")
    ap.add_argument("--ledger", default="")
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
