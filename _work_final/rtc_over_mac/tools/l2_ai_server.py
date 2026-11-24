#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI server = DOWNLINK sender (the contention point that matches the sim).

Runs on the laptop behind the AP. The AP bridges server->Pi, so all traffic
here competes in the AP's egress queue toward the STA -- the same place where
ns3-agent-dev_l2 puts QuotaWifiQueueScheduler / AiFirstWifiQueueScheduler.

Responsibilities:
  * dedup requests by msg_id (one response per request, always ACK)
  * generate bulk downlink traffic (flow >= 1) to keep the queue busy
  * run the scheduler (fifo / quota / ai-first / both) on the downlink queue
  * pace at --rate-mbps (or not: --no-pacing makes the MAC queue the bottleneck)
  * response feedback: ACK timeout -> resend (max N)
"""
import argparse
import json
import os
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import (ETH_AI, ETH_ACK, ETH_BULK, KIND_REQ, KIND_RESP,
                          build_frame, parse_frame, mac_bytes)
from l2_ai_sched import Item, Scheduler

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
        self.seen = set()
        self.outstanding = {}
        self.stats = {
            "requests_rx": 0, "requests_dup": 0, "responses_sent": 0,
            "responses_resent": 0, "responses_acked": 0,
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
              iface=self.iface, verbose=0, realtime=False)
        return len(frame)

    # ---------- RX ----------
    def on_frame(self, pkt):
        p = parse_frame(bytes(pkt))
        if not p or p["src"] == self.src:
            return
        if p["ethertype"] == ETH_ACK:
            with self.lock:
                self.outstanding.pop(p["msg_id"], None)
            self.stats["responses_acked"] += 1
            return
        if p["ethertype"] == ETH_AI and p["kind"] == KIND_REQ:
            mid = p["msg_id"]
            with self.lock:
                self.stats["requests_rx"] += 1
                dup = mid in self.seen
                self.seen.add(mid)
                if dup:
                    self.stats["requests_dup"] += 1
            # always ACK (idempotent); only answer the first copy
            self.send(ETH_ACK, 0, mid, 3, 0, struct.pack("!I", 0))
            if dup:
                return
            item = Item(0, mid, KIND_RESP, p["t0_ns"],
                        self.a.response_bytes + 20)
            with self.lock:
                self.sched.enqueue(item)

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
            batch, batch_bytes = [], 0
            with self.lock:
                while len(batch) < self.a.send_batch:
                    item = self.sched.pop()
                    if item is None:
                        break
                    if tokens < item.nbytes + 12:
                        self.sched._plain(item)
                        break
                    tokens -= item.nbytes + 12
                    batch.append(item)
            if not batch:
                time.sleep(0.0005)
                continue
            for item in batch:
                eth = ETH_BULK if item.kind == 2 else ETH_AI
                payload = b"\x00" * max(0, item.nbytes - 20)
                try:
                    n = self.send(eth, item.flow, item.msg_id,
                                  KIND_RESP if item.kind == 1 else 2,
                                  item.t0_ns, payload)
                except Exception as exc:
                    self.log("send_err", item.flow, item.msg_id, str(exc))
                    continue
                with self.lock:
                    self.stats["send_bytes"] += n
                    if item.kind == 1:
                        self.stats["responses_sent"] += 1
                        self.outstanding[item.msg_id] = {
                            "attempts": 1, "last_ns": time.monotonic_ns(),
                            "item": item,
                        }
                    else:
                        self.stats["bulk_sent"] += 1

    # ---------- response retransmit ----------
    def retx_loop(self):
        while not self.stop:
            now = time.monotonic_ns()
            with self.lock:
                for mid, rec in list(self.outstanding.items()):
                    if rec["attempts"] > self.a.max_resend:
                        continue
                    if (now - rec["last_ns"]) / 1e6 >= self.a.ack_timeout_ms:
                        rec["attempts"] += 1
                        rec["last_ns"] = now
                        it = rec["item"]
                        self.sched.enqueue(Item(0, mid, 1, it.t0_ns,
                                                it.nbytes, rec["attempts"]))
                        self.stats["responses_resent"] += 1
            time.sleep(0.01)

    def run(self):
        sn = AsyncSniffer(iface=self.iface,
                          filter="ether proto 0x88b6 or ether proto 0x88b8",
                          prn=self.on_frame, store=0)
        sn.start()
        ts = [threading.Thread(target=f, daemon=True)
              for f in (self.gen_loop, self.tx_loop, self.retx_loop)]
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
               "bulk_mbps": self.a.bulk_mbps}
        res.update(self.stats)
        res.update(self.sched.stats())
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
    ap.add_argument("--ack-timeout-ms", type=float, default=60.0)
    ap.add_argument("--max-resend", type=int, default=8)
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
    import random  # noqa: F401
    main()
