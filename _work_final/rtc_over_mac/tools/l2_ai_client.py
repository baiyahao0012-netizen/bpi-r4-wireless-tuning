#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI client: feedback loop + quota admission (enqueue) + AI-first (dequeue).

Runs on the Pi with AF_PACKET (needs root/CAP_NET_RAW), sends to the laptop MAC
through the AP bridge.

Mechanisms (mirroring contrib/genai of ns3-agent-dev_l2):
  quota   : per-flow byte fair share, MinPerFlow guarantee, eviction of the
            most-over-quota flow when a small flow needs room (admission, drops).
  ai-first: service order inside the shim queue: AI flow first, FCFS otherwise.
  feedback: outstanding table; local drop or ACK timeout -> resend same bytes
            (max N), ACK -> retire; server dedups by msg_id.

The shim queue is the bottleneck by construction (token bucket pacing below the
link rate), which is exactly the regime where the policy is supposed to matter.
"""
import argparse
import collections
import json
import os
import random
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import (ETH_AI, ETH_ACK, ETH_BULK, KIND_REQ, KIND_BULK,
                          build_frame, parse_frame, mac_bytes)


class Item:
    __slots__ = ("flow", "msg_id", "kind", "t0_ns", "nbytes", "enq_ns", "attempt")

    def __init__(self, flow, msg_id, kind, t0_ns, nbytes, attempt=0):
        self.flow = flow
        self.msg_id = msg_id
        self.kind = kind
        self.t0_ns = t0_ns
        self.nbytes = nbytes
        self.enq_ns = time.monotonic_ns()
        self.attempt = attempt


class Link:
    def __init__(self, iface, src_mac, dst_mac):
        self.src = mac_bytes(src_mac)
        self.dst = mac_bytes(dst_mac)
        self.sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                                  socket.htons(0x0003))
        self.sock.bind((iface, 0))
        self.sock.settimeout(0.05)
        self.iface = iface

    def send(self, ethertype, flow, msg_id, kind, t0_ns, payload=b""):
        frame = build_frame(self.dst, self.src, ethertype, flow, msg_id, kind,
                            t0_ns, payload)
        self.sock.send(frame)
        return len(frame)


class Scheduler:
    """The two schedulers, on the same queue."""

    def __init__(self, mode, capacity, min_per_flow):
        self.mode = mode              # fifo | quota | ai-first | both
        self.ai_evict = False         # sim AiFirst has no enqueue eviction
        self.capacity = capacity
        self.min_per_flow = min_per_flow
        self.queues = collections.OrderedDict()   # flow -> deque[Item]
        self.npackets = 0
        self.nbytes = 0
        self.max_depth = 0
        self.evictions = 0
        self.rejections = 0
        self.dropped = collections.Counter()      # flow -> count

    def _enqueue_plain(self, item):
        self.queues.setdefault(item.flow, collections.deque()).append(item)
        self.npackets += 1
        self.nbytes += item.nbytes
        self.max_depth = max(self.max_depth, self.npackets)

    def enqueue(self, item, log):
        full = self.npackets >= self.capacity
        if full and self.ai_evict and self.mode in ("ai-first", "both") and item.flow == 0:
            # AI arrival may evict the oldest bulk frame (AI-first admission)
            if self._evict_bulk(log):
                full = False
        if full and self.mode in ("quota", "both"):
            # byte fair share over active flows
            nflows = max(1, len(self.queues))
            share = max(self.min_per_flow * 1484, self.capacity * 1484 // nflows)
            own = sum(i.nbytes for i in self.queues.get(item.flow, ()))
            if own < share:
                victim = self._pick_victim()
                if victim is not None:
                    vq = self.queues[victim.flow]
                    v = vq.popleft()
                    self.npackets -= 1
                    self.nbytes -= v.nbytes
                    self.evictions += 1
                    self.dropped[victim.flow] += 1
                    log("evict", v.flow, v.msg_id, "quota_evict")
                    full = False
            if full:
                self.rejections += 1
                self.dropped[item.flow] += 1
                log("reject", item.flow, item.msg_id, "quota_reject")
                return False
        elif full:
            self.rejections += 1
            self.dropped[item.flow] += 1
            log("reject", item.flow, item.msg_id, "queue_full")
            return False
        self._enqueue_plain(item)
        return True

    def _evict_bulk(self, log):
        """Remove the oldest bulk (flow>0) head; True if one was evicted."""
        best = None
        for flow in self.queues:
            if flow == 0:
                continue
            q = self.queues[flow]
            if q and (best is None or q[0].enq_ns < best[0]):
                best = (q[0].enq_ns, q)
        if best is None:
            return False
        q = best[1]
        v = q.popleft()
        self.npackets -= 1
        self.nbytes -= v.nbytes
        self.evictions += 1
        self.dropped[v.flow] += 1
        log("evict", v.flow, v.msg_id, "ai_first_evict")
        return True

    def _pick_victim(self):
        best, best_over = None, None
        nflows = max(1, len(self.queues))
        share = self.nbytes // nflows
        for flow, q in self.queues.items():
            if not q:
                continue
            over = sum(i.nbytes for i in q) - share
            if over > 0 and (best_over is None or over > best_over):
                best, best_over = q[0], over
        return best

    def pop(self):
        """Return the next item according to the dequeue policy."""
        if self.mode in ("ai-first", "both") and self.queues.get(0):
            q = self.queues[0]
        else:
            q = None
            oldest = None
            for flow in self.queues:
                cand = self.queues[flow]
                if not cand:
                    continue
                if oldest is None or cand[0].enq_ns < oldest:
                    oldest = cand[0].enq_ns
                    q = cand
        if q is None:
            return None
        item = q.popleft()
        self.npackets -= 1
        self.nbytes -= item.nbytes
        return item


class Client:
    def __init__(self, a):
        self.a = a
        self.link = Link(a.iface, a.src_mac, a.dst_mac)
        self.sched = Scheduler(a.mode, a.qcap, a.min_per_flow)
        self.sched.ai_evict = a.ai_evict
        self.lock = threading.RLock()
        self.stop = False
        self.outstanding = {}      # msg_id -> dict(bytes=Item, attempts, last_ns)
        self.ttft_us = []
        self.requests = []
        self.delivered = 0
        self.resends = 0
        self.events = []
        self.csv = open(a.csv, "w", buffering=1) if a.csv else None
        if self.csv:
            self.csv.write("t_ns,event,flow,msg_id,detail\n")
        self.bulk_flow_count = a.flows

    def log(self, event, flow, msg_id, detail=""):
        with self.lock:
            self.events.append((time.monotonic_ns(), event, flow, msg_id, detail))
            if self.csv:
                self.csv.write("%d,%s,%d,%d,%s\n" %
                               (time.monotonic_ns(), event, flow, msg_id, detail))

    # ---------- RX ----------
    def rx_loop(self):
        while not self.stop:
            try:
                raw = self.link.sock.recv(65535)
            except socket.timeout:
                continue
            p = parse_frame(raw)
            if not p:
                continue
            if p["src"] == self.link.src:
                continue  # our own outgoing frame looped back by AF_PACKET
            if p["ethertype"] == ETH_ACK:
                with self.lock:
                    self.outstanding.pop(p["msg_id"], None)
                continue
            if p["ethertype"] == ETH_AI and p["kind"] == 1:   # response
                with self.lock:
                    rec = self.outstanding.pop(p["msg_id"], None)
                if rec is not None:
                    self.ttft_us.append((time.monotonic_ns() - rec["t0_ns"]) / 1000.0)
                    self.delivered += 1
                # ack the response so the server can retire it
                self.link.send(ETH_ACK, 0, p["msg_id"], 3, 0, b"\x00\x00\x00\x00")
                self.log("ack_resp", 0, p["msg_id"], "")
            elif p["ethertype"] == ETH_BULK:
                self.log("bulk_rx", p["flow"], p["msg_id"], "")

    # ---------- TX ----------
    def tx_loop(self):
        rate = self.a.rate_mbps * 1e6 / 8.0     # bytes/s
        burst = max(1500.0, rate * 0.01)
        tokens = burst
        last = time.monotonic()
        while not self.stop:
            now = time.monotonic()
            tokens = min(burst, tokens + (now - last) * rate)
            last = now
            with self.lock:
                item = self.sched.pop()
            if item is None:
                time.sleep(0.001)
                continue
            if tokens < item.nbytes + 12:
                with self.lock:
                    self.sched._enqueue_plain(item)   # put back at tail
                time.sleep(0.001)
                continue
            tokens -= item.nbytes + 12
            eth = ETH_BULK if item.kind == KIND_BULK else ETH_AI
            try:
                payload = b"\x00" * max(0, item.nbytes - 20)
                self.link.send(eth, item.flow, item.msg_id, item.kind, item.t0_ns, payload)
            except OSError as exc:
                self.log("send_err", item.flow, item.msg_id, str(exc))
                continue
            key = (item.flow, item.msg_id)
            self.log("tx", item.flow, item.msg_id, "attempt=%d" % item.attempt)
            if item.kind != KIND_BULK:
                with self.lock:
                    rec = self.outstanding.get(item.msg_id)
                    if rec is None:
                        self.outstanding[item.msg_id] = {
                            "t0_ns": item.t0_ns, "attempts": 1,
                            "last_ns": time.monotonic_ns(), "item": item,
                        }
                    else:
                        rec["attempts"] += 1
                        rec["last_ns"] = time.monotonic_ns()
                        rec["item"] = item

    # ---------- generator ----------
    def gen_loop(self):
        a = self.a
        t_end = time.monotonic() + a.seconds
        msg_id = a.msg_base
        next_ai = time.monotonic()
        next_bulk = time.monotonic()
        bulk_pkt = 1400
        bulk_pps = (a.bulk_mbps * 1e6 / 8.0) / bulk_pkt
        bulk_carry = 0.0
        while time.monotonic() < t_end and not self.stop:
            now = time.monotonic()
            if now >= next_ai:
                t0 = time.monotonic_ns()
                payload = b"Q%08d" % msg_id
                item = Item(0, msg_id, KIND_REQ, t0, 8 + 20)  # payload+hdr
                with self.lock:
                    ok = True
                    if a.ai_drop > 0 and random.random() < a.ai_drop:
                        ok = False
                        self.sched.rejections += 1
                        self.sched.dropped[0] += 1
                        self.log("reject", 0, msg_id, "injected")
                    else:
                        ok = self.sched.enqueue(item, self.log)
                if not ok:
                    # local drop -> immediate resend (design: no RTT wait)
                    r = Item(0, msg_id, KIND_REQ, t0, 8 + 20, attempt=1)
                    with self.lock:
                        self.sched.enqueue(r, self.log)
                    self.resends += 1
                self.requests.append(msg_id)
                msg_id += 1
                next_ai += a.ai_interval_ms / 1000.0
            if a.bulk_mbps > 0 and now >= next_bulk:
                bulk_carry += bulk_pps / 100.0
                n = int(bulk_carry)
                bulk_carry -= n
                for k in range(n):
                    flow = 1 + (k % max(1, a.flows))
                    item = Item(flow, 0, KIND_BULK, 0, bulk_pkt)
                    with self.lock:
                        self.sched.enqueue(item, self.log)
                next_bulk += 0.01
            time.sleep(0.0005)

    # ---------- retransmit sweep ----------
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
                        to_resend.append(mid)
            for mid in to_resend:
                with self.lock:
                    rec = self.outstanding.get(mid)
                    if rec is None:
                        continue
                    it = rec["item"]
                    r = Item(it.flow, it.msg_id, it.kind, it.t0_ns, it.nbytes,
                             attempt=rec["attempts"])
                if self.sched.enqueue(r, self.log):
                    self.resends += 1
                    self.log("resend", r.flow, r.msg_id, "attempt=%d" % r.attempt)
            time.sleep(0.010)

    def run(self):
        import traceback

        def guarded(fn):
            def wrap():
                try:
                    fn()
                except Exception:
                    traceback.print_exc()
            return wrap

        th = [threading.Thread(target=guarded(f), daemon=True) for f in
              (self.rx_loop, self.tx_loop, self.gen_loop, self.retx_loop)]
        for t in th:
            t.start()
        time.sleep(self.a.seconds)
        self.stop = True
        time.sleep(0.3)

    def summary(self):
        tt = sorted(self.ttft_us)
        def pct(q):
            return tt[min(len(tt) - 1, int(len(tt) * q))] if tt else None
        return {
            "mode": self.a.mode,
            "requests": len(self.requests),
            "delivered": self.delivered,
            "delivery_ratio": round(self.delivered / max(1, len(self.requests)), 4),
            "ttft_p50_us": round(pct(0.5), 1) if tt else None,
            "ttft_p95_us": round(pct(0.95), 1) if tt else None,
            "resends": self.resends,
            "evictions": self.sched.evictions,
            "rejections": self.sched.rejections,
            "max_queue_depth": self.sched.max_depth,
            "drops_by_flow": dict(self.sched.dropped),
            "rate_mbps": self.a.rate_mbps,
            "bulk_mbps_offered": self.a.bulk_mbps,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fifo", "quota", "ai-first", "both"],
                    default="fifo")
    ap.add_argument("--iface", default="wlan1")
    ap.add_argument("--src-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--dst-mac", required=True)
    ap.add_argument("--seconds", type=float, default=20)
    ap.add_argument("--rate-mbps", type=float, default=20.0)
    ap.add_argument("--bulk-mbps", type=float, default=0.0)
    ap.add_argument("--flows", type=int, default=4)
    ap.add_argument("--flow-pps", type=int, default=4)
    ap.add_argument("--ai-interval-ms", type=float, default=100.0)
    ap.add_argument("--qcap", type=int, default=500)
    ap.add_argument("--min-per-flow", type=int, default=20)
    ap.add_argument("--ack-timeout-ms", type=float, default=50.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--ai-evict", action="store_true",
                    help="enable enqueue eviction for AI (NOT in sim AiFirst)")
    ap.add_argument("--msg-base", type=int, default=0)
    ap.add_argument("--ai-drop", type=float, default=0.0,
                    help="inject local AI drops (simulated MAC/TC loss)")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()

    c = Client(a)
    try:
        c.run()
    except KeyboardInterrupt:
        pass
    print("RESULT " + json.dumps(c.summary(), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()










