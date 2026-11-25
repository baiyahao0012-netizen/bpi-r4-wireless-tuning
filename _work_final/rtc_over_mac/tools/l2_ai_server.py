#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI server (downlink sender) with a three-state feedback machine.

States per request id:  queued -> inflight -> done
  * registration happens BEFORE enqueue (mirrors AiServerApplication::Store
    at ai-server-application.cc:347 which precedes the send at :352);
  * enqueue rejection / send error put the record back to queued and count it
    (mirrors DropBeforeEnqueue -> ResendTextChunk);
  * a duplicate request whose response is not done re-sends the response
    (dedup means "infer once", not "transmit once");
  * an inflight response older than --resp-timeout-ms is re-enqueued
    (the app-layer stand-in for a missing MAC-level DroppedMpdu event).

--ack-drop / --resp-drop inject loss so the recovery loops can be measured.
"""
import argparse
import json
import os
import random
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import (ETH_AI, ETH_ACK, ETH_BULK, KIND_REQ, KIND_RESP,
                          build_frame, parse_frame, mac_bytes)
from l2_ai_sched import Item, Scheduler

import collections
from scapy.all import AsyncSniffer, Ether, Raw, conf, sendp
from scapy.arch import get_if_addr


class Server:
    def __init__(self, a, iface):
        self.a = a
        self.iface = iface
        self.src = mac_bytes(a.src_mac)
        self.dst = mac_bytes(a.client_mac)
        self.sched = Scheduler(a.mode, a.capacity, a.min_per_flow, self.log)
        self.lock = threading.RLock()
        self.stop = False
        self.records = {}          # mid -> {state, item, attempts, last_ns}
        self.ackq = collections.deque()   # ACKs are sent off the capture thread
        self.stats = {
            "requests_rx": 0, "requests_dup": 0,
            "responses_sent": 0, "responses_acked": 0,
            "resp_dup_resend": 0, "enqueue_reject": 0, "send_err_retry": 0,
            "retx_timeout": 0, "resp_lost": 0, "ack_dropped": 0, "done": 0,
            "resend_cap_hit": 0,
            "bulk_sent": 0, "send_bytes": 0,
        }
        self.csv = open(a.csv, "w", buffering=1) if a.csv else None
        if self.csv:
            self.csv.write("t_ns,event,flow,msg_id,detail\n")

    def log(self, event, flow, msg_id, detail=""):
        with self.lock:
            if self.csv:
                self.csv.write("%d,%s,%d,%d,%s\n" %
                               (time.monotonic_ns(), event, flow, msg_id, detail))

    def send(self, ethertype, flow, msg_id, kind, t0_ns, payload):
        frame = build_frame(self.dst, self.src, ethertype, flow, msg_id, kind,
                            t0_ns, payload)
        sendp(Ether(dst=self.dst, src=self.src, type=ethertype) / Raw(frame[14:]),
              iface=self.iface, verbose=0)
        return len(frame)

    # ---------- record helpers ----------
    def _enqueue(self, rec, mid):
        ok = self.sched.enqueue(rec["item"])
        if ok:
            rec["state"] = "queued"
        else:
            rec["state"] = "rejected"
            self.stats["enqueue_reject"] += 1
            self.log("enqueue_reject", 0, mid, "")
        return ok

    def _new_item(self, mid, t0_ns):
        return Item(0, mid, KIND_RESP, t0_ns, self.a.response_bytes + 20)

    # ---------- RX ----------
    def on_frame(self, pkt):
        p = parse_frame(bytes(pkt))
        if not p or p["src"] == self.src:
            return
        if p["ethertype"] == ETH_ACK:
            with self.lock:
                rec = self.records.get(p["msg_id"])
                if rec is not None:
                    rec["state"] = "done"
                    self.stats["done"] += 1
                self.stats["responses_acked"] += 1
                self.log("ack_recv", 0, p["msg_id"], "")
            return
        if p["ethertype"] == ETH_AI and p["kind"] == KIND_REQ:
            mid = p["msg_id"]
            with self.lock:
                self.stats["requests_rx"] += 1
                rec = self.records.get(mid)
                if rec is None:
                    rec = {"state": "queued", "item": self._new_item(mid, p["t0_ns"]),
                           "attempts": 0, "last_ns": time.monotonic_ns()}
                    self.records[mid] = rec
                    enqueue_needed = True
                elif rec["state"] != "done":
                    self.stats["requests_dup"] += 1
                    if rec["attempts"] < self.a.max_resend:
                        # duplicate request, response not confirmed: retransmit it
                        self.stats["resp_dup_resend"] += 1
                        rec["item"] = self._new_item(mid, p["t0_ns"])
                        enqueue_needed = True
                        self.log("dup_resend", 0, mid, "")
                    else:
                        self.stats["resend_cap_hit"] = self.stats.get("resend_cap_hit", 0) + 1
                else:
                    self.stats["requests_dup"] += 1
                    enqueue_needed = False
            # always ACK the request (idempotent), sent asynchronously
            if random.random() >= self.a.ack_drop:
                with self.lock:
                    self.ackq.append(mid)
            else:
                self.stats["ack_dropped"] += 1
            if enqueue_needed:
                with self.lock:
                    self._enqueue(rec, mid)

    # ---------- ACK sender ----------
    def ack_loop(self):
        while not self.stop:
            with self.lock:
                mid = self.ackq.popleft() if self.ackq else None
            if mid is None:
                time.sleep(0.001)
                continue
            try:
                self.send(ETH_ACK, 0, mid, 3, 0, struct.pack("!I", 0))
            except Exception:
                pass

    # ---------- bulk generator ----------
    def gen_loop(self):
        pkt = 1400
        pps = (self.a.bulk_mbps * 1e6 / 8.0) / pkt
        carry = 0.0
        next_t = time.monotonic()
        while not self.stop:
            now = time.monotonic()
            if now < next_t:
                time.sleep(0.001)
                continue
            carry += pps / 100.0
            n = int(carry)
            carry -= n
            for k in range(n):
                flow = 1 + (k % self.a.flows)
                with self.lock:
                    self.sched.enqueue(Item(flow, 0, 2, 0, pkt))
            next_t += 0.01

    # ---------- TX ----------
    def tx_loop(self):
        rate = self.a.rate_mbps * 1e6 / 8.0
        burst = max(1500.0, rate * 0.01)
        tokens = burst
        last = time.monotonic()
        while not self.stop:
            now = time.monotonic()
            if self.a.pacing:
                tokens = min(burst, tokens + (now - last) * rate)
            else:
                tokens = 1e18
            last = now
            batch = []
            with self.lock:
                for _ in range(self.a.send_batch):
                    item = self.sched.pop()
                    if item is None:
                        break
                    if tokens < item.nbytes + 12:
                        self.sched._plain(item)
                        break
                    tokens -= item.nbytes + 12
                    batch.append(item)
            for item in batch:
                if item.kind == KIND_RESP:
                    with self.lock:
                        rec = self.records.get(item.msg_id)
                    if rec is None:
                        continue
                    # simulate air loss AFTER the record is inflight
                    if random.random() < self.a.resp_drop:
                        with self.lock:
                            rec["state"] = "inflight"
                            rec["last_ns"] = time.monotonic_ns()
                            rec["attempts"] += 1
                            self.stats["resp_lost"] += 1
                        self.log("resp_lost", 0, item.msg_id, "")
                        continue
                    try:
                        n = self.send(ETH_AI, 0, item.msg_id, KIND_RESP,
                                      item.t0_ns, b"\x00" * (item.nbytes - 20))
                    except Exception as exc:
                        with self.lock:
                            rec["state"] = "queued"
                            self.stats["send_err_retry"] += 1
                            self.sched.enqueue(rec["item"])
                        self.log("send_err", 0, item.msg_id, str(exc))
                        continue
                    with self.lock:
                        rec["state"] = "inflight"
                        rec["last_ns"] = time.monotonic_ns()
                        rec["attempts"] += 1
                        self.stats["responses_sent"] += 1
                        self.log("resp_sent", 0, item.msg_id, "attempt=%d" % rec["attempts"])
                        self.stats["send_bytes"] += n
                else:
                    try:
                        n = self.send(ETH_BULK, item.flow, 0, 2, 0,
                                      b"\x00" * (item.nbytes - 20))
                        with self.lock:
                            self.stats["bulk_sent"] += 1
                            self.stats["send_bytes"] += n
                    except Exception:
                        pass

    # ---------- retransmit sweep ----------
    def retx_loop(self):
        while not self.stop:
            now = time.monotonic_ns()
            retry = []
            with self.lock:
                for mid, rec in self.records.items():
                    if rec["state"] == "done":
                        continue
                    if rec["attempts"] > self.a.max_resend:
                        continue
                    if rec["state"] == "rejected":
                        retry.append(mid)
                    elif (now - rec["last_ns"]) / 1e6 >= self.a.resp_timeout_ms:
                        rec["attempts"] += 1
                        rec["item"] = self._new_item(mid, rec["item"].t0_ns)
                        self.stats["retx_timeout"] += 1
                        retry.append(mid)
                        self.log("retx_timeout", 0, mid, "")
            for mid in retry:
                with self.lock:
                    rec = self.records.get(mid)
                    if rec is not None:
                        self._enqueue(rec, mid)
            time.sleep(0.01)

    def run(self):
        sn = AsyncSniffer(iface=self.iface,
                          filter="ether proto 0x88b6 or ether proto 0x88b8",
                          prn=self.on_frame, store=0)
        sn.start()
        ts = [threading.Thread(target=f, daemon=True)
              for f in (self.ack_loop, self.gen_loop, self.tx_loop, self.retx_loop)]
        for t in ts:
            t.start()
        time.sleep(self.a.seconds)
        self.stop = True
        time.sleep(0.3)
        try:
            sn.stop()
        except Exception:
            pass
        res = {"role": "server(downlink)", "mode": self.a.mode,
               "pacing": self.a.pacing, "rate_mbps": self.a.rate_mbps,
               "bulk_mbps": self.a.bulk_mbps,
               "ack_drop": self.a.ack_drop, "resp_drop": self.a.resp_drop}
        res.update(self.stats)
        res.update(self.sched.stats())
        res["unique_requests"] = len(self.records)
        return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fifo", "quota", "ai-first", "both"],
                    default="fifo")
    ap.add_argument("--ip", default="192.168.240.2")
    ap.add_argument("--src-mac", default="40:c2:ba:52:70:95")
    ap.add_argument("--client-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--seconds", type=float, default=14)
    ap.add_argument("--rate-mbps", type=float, default=10.0)
    ap.add_argument("--pacing", dest="pacing", action="store_true", default=True)
    ap.add_argument("--no-pacing", dest="pacing", action="store_false")
    ap.add_argument("--bulk-mbps", type=float, default=0.0)
    ap.add_argument("--flows", type=int, default=4)
    ap.add_argument("--capacity", type=int, default=200)
    ap.add_argument("--min-per-flow", type=int, default=20)
    ap.add_argument("--response-bytes", type=int, default=1200)
    ap.add_argument("--send-batch", type=int, default=8)
    ap.add_argument("--resp-timeout-ms", type=float, default=80.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--ack-drop", type=float, default=0.0)
    ap.add_argument("--resp-drop", type=float, default=0.0)
    ap.add_argument("--csv", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    dev = None
    for i in conf.ifaces.values():
        try:
            if get_if_addr(i) == a.ip:
                dev = i
                break
        except Exception:
            pass
    if dev is None:
        raise SystemExit("no interface with ip %s" % a.ip)
    res = Server(a, dev).run()
    text = "RESULT " + json.dumps(res, ensure_ascii=False)
    print(text, flush=True)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()



