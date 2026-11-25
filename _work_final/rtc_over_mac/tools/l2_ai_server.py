#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI server (downlink sender): feedback state machine + deterministic
injection + per-message ledger + L2 echo responder.

States: queued -> inflight -> done.
  * record created before enqueue (Store before send);
  * enqueue rejection / send failure -> queued, counted;
  * duplicate request with state != done -> resend response (dedup = infer once);
  * inflight older than --resp-timeout-ms -> retransmit (timeout regime);
  * --drop-resp mid:n   : the first n sends of mid are pretended-lost (timeout path)
  * --fail-resp mid:n   : the first n sends of mid fail immediately (event path)
  * --drop-ack-req mid:n: suppress the first n request-ACKs for mid
Ledger fields: constructed, dup_requests, injected_drop, sends[{n,t,ack,sendp_us}]
"""
import argparse
import collections
import json
import os
import random
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l2_ai_common import (ETH_AI, ETH_ACK, ETH_BULK, ETH_ECHO, KIND_REQ,
                          KIND_RESP, build_frame, parse_frame, mac_bytes)
from l2_ai_sched import Item, Scheduler
from fast_tx import PcapTx

from scapy.all import AsyncSniffer, Ether, Raw, conf, sendp
from scapy.arch import get_if_addr


def parse_spec(s):
    out = {}
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        mid, n = part.split(":")
        out[int(mid)] = int(n)
    return out


class Server:
    def __init__(self, a, iface):
        self.a = a
        self.iface = iface
        self.src = mac_bytes(a.src_mac)
        self.dst = mac_bytes(a.client_mac)
        self.sched = Scheduler(a.mode, a.capacity, a.min_per_flow, self.log)
        self.lock = threading.RLock()
        self.stop = False
        self.records = {}
        self.order = collections.deque()      # insertion order for bounded history
        self.ackq = collections.deque()
        self.echoq = collections.deque()
        self.drop_resp = parse_spec(a.drop_resp)
        self.fail_resp = parse_spec(a.fail_resp)
        self.drop_ack_req = parse_spec(a.drop_ack_req)
        self.ack_sent = collections.Counter()
        self.stats = {
            "requests_rx": 0, "requests_dup": 0, "responses_sent": 0,
            "responses_acked": 0, "resp_dup_resend": 0, "enqueue_reject": 0,
            "send_err_retry": 0, "retx_timeout": 0, "injected_drop": 0,
            "constructed": 0, "ack_req_dropped": 0,
            "resend_cap_hit": 0, "sendp_calls": 0, "ack_resp_recv": 0,
            "echo_rx": 0, "bulk_sent": 0, "dup_resend_limited": 0,
            "buffer_evicted": 0, "abandoned": 0, "retry_rejected": 0,
            "rejected_by_flow": {}, "evicted_by_flow": {},
        }
        self.created_total = 0
        self.attempts_ever = 0
        self.tx = PcapTx(a.ip) if getattr(a, "fast_tx", False) else None
        self.csv = open(a.csv, "w", buffering=1) if a.csv else None
        if self.csv:
            self.csv.write("t_ns,event,flow,msg_id,detail\n")

    def log(self, event, flow, msg_id, detail=""):
        with self.lock:
            if self.csv:
                self.csv.write("%d,%s,%d,%d,%s\n" %
                               (time.monotonic_ns(), event, flow, msg_id, detail))

    def send(self, ethertype, flow, msg_id, kind, t0_ns, payload, flags=0):
        frame = build_frame(self.dst, self.src, ethertype, flow, msg_id, kind,
                            t0_ns, payload, flags)
        t0 = time.monotonic_ns()
        if self.tx is not None:
            self.tx.send(frame)
        else:
            sendp(Ether(dst=self.dst, src=self.src, type=ethertype) / Raw(frame[14:]),
                  iface=self.iface, verbose=0)
        return len(frame), (time.monotonic_ns() - t0) / 1000.0

    # ---------- record helpers ----------
    def _new_item(self, mid, t0_ns):
        return Item(0, mid, KIND_RESP, t0_ns, self.a.response_bytes + 20)

    def _enqueue(self, rec, mid):
        ok = self.sched.enqueue(rec["item"])
        if ok:
            rec["state"] = "queued"
        else:
            # admission rejected: this is an EVENT, not a terminal state.
            # Simulation: HasToDropBeforeEnqueue -> DropBeforeEnqueue ->
            # OnTextQueueDiscDropped -> ScheduleNow (immediate retry).
            rec["state"] = "rejected"
            rec["reject_ns"] = time.monotonic_ns()
            rec["reject_retries"] = rec.get("reject_retries", 0) + 1
            self.stats["enqueue_reject"] += 1
            self.stats["rejected_by_flow"][rec["item"].flow] = \
                self.stats["rejected_by_flow"].get(rec["item"].flow, 0) + 1
            self.log("enqueue_reject", 0, mid, "retry=%d" % rec["reject_retries"])
        return ok

    # ---------- RX ----------
    def on_frame(self, pkt):
        p = parse_frame(bytes(pkt))
        if not p or p["src"] == self.src:
            return
        if p["ethertype"] == ETH_ECHO:
            self.stats["echo_rx"] += 1
            # answer immediately: echo RTT is the single-clock floor probe
            try:
                self.send(ETH_ECHO, p["flow"], p["msg_id"], 0, p["t0_ns"], p["payload"])
            except Exception:
                pass
            return
        if p["ethertype"] == ETH_ACK:
            mid = p["msg_id"]
            now = time.monotonic_ns()
            with self.lock:
                rec = self.records.get(mid)
                if rec is not None:
                    for s in reversed(rec["sends"]):
                        if s["ack"] == "none":
                            s["ack"] = "recv"
                            s["ack_after_us"] = (now - s["t_ns"]) / 1000.0
                            break
                    rec["state"] = "done"
                self.stats["responses_acked"] += 1
                self.stats["ack_resp_recv"] += 1
            return
        if p["ethertype"] == ETH_AI and p["kind"] == KIND_REQ:
            mid = p["msg_id"]
            send_ack = True
            with self.lock:
                self.stats["requests_rx"] += 1
                rec = self.records.get(mid)
                if rec is None:
                    rec = {"state": "queued", "item": self._new_item(mid, p["t0_ns"]),
                           "recv_ns": time.monotonic_ns(), "attempts": 0,
                           "last_ns": time.monotonic_ns(), "last_send_ns": 0, "constructed": 1,
                           "dup_requests": 0, "injected_drop": 0, "fail_send": 0,
                           "sends": []}
                    self.records[mid] = rec
                    self.order.append(mid)
                    self.created_total += 1
                    self.stats["constructed"] += 1
                    # bounded history (AiTextRetransmitBuffer depth), evict oldest done
                    while len(self.order) > self.a.buffer_depth:
                        old = self.order.popleft()
                        orec = self.records.get(old)
                        if orec is not None and orec["state"] == "done":
                            del self.records[old]
                            self.stats["buffer_evicted"] += 1
                        else:
                            self.order.append(old)
                            break
                    need = True
                elif rec["state"] != "done":
                    self.stats["requests_dup"] += 1
                    rec["dup_requests"] += 1
                    now_ns = time.monotonic_ns()
                    rate_ok = (rec["attempts"] == 0 or
                               (now_ns - rec["last_send_ns"]) >= self.a.resp_timeout_ms * 0.5 * 1e6)
                    need = rec["attempts"] <= self.a.max_resend and rate_ok
                    if not rate_ok and rec["attempts"] < self.a.max_resend:
                        self.stats["dup_resend_limited"] = self.stats.get("dup_resend_limited", 0) + 1
                    if need:
                        self.stats["resp_dup_resend"] += 1
                        rec["item"] = self._new_item(mid, p["t0_ns"])
                        self.log("dup_resend", 0, mid, "")
                    else:
                        self.stats["resend_cap_hit"] += 1
                else:
                    self.stats["requests_dup"] += 1
                    rec["dup_requests"] += 1
                    need = False
                n_ack = self.ack_sent[mid] + 1
                if self.drop_ack_req.get(mid, 0) >= n_ack:
                    send_ack = False
                    self.stats["ack_req_dropped"] += 1
                else:
                    self.ack_sent[mid] = n_ack
            if send_ack:
                with self.lock:
                    self.ackq.append(mid)
            if need:
                with self.lock:
                    self._enqueue(rec, mid)

    # ---------- ACK / echo senders ----------
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

    # ---------- bulk ----------
    def gen_loop(self):
        if self.a.bulk_delay > 0:
            time.sleep(self.a.bulk_delay)
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
            tokens = min(burst, tokens + (now - last) * rate) if self.a.pacing else 1e18
            last = now
            batch = []
            with self.lock:
                for _ in range(self.a.send_batch):
                    head = self.sched.peek()
                    if head is None:
                        break
                    if tokens < head.nbytes + 12:
                        break
                    tokens -= head.nbytes + 12
                    batch.append(self.sched.pop())
            for item in batch:
                if item.kind != KIND_RESP:
                    try:
                        self.send(ETH_BULK, item.flow, 0, 2, 0,
                                  b"\x00" * (item.nbytes - 20))
                        with self.lock:
                            self.stats["bulk_sent"] += 1
                            self.sched.note_served(item)
                    except Exception:
                        pass
                    continue
                mid = item.msg_id
                with self.lock:
                    rec = self.records.get(mid)
                if rec is None:
                    continue
                n = rec["attempts"] + 1
                now_ns = time.monotonic_ns()
                if self.drop_resp.get(mid, 0) >= n:
                    with self.lock:
                        rec["state"] = "inflight"
                        rec["attempts"] = n
                        rec["last_ns"] = now_ns
                        rec["last_send_ns"] = now_ns
                        rec["injected_drop"] += 1
                        rec["sends"].append({"n": n, "t_ns": now_ns, "ack": "none",
                                             "sendp_us": 0.0, "injected": "drop"})
                        self.stats["injected_drop"] += 1
                        self.attempts_ever += 1
                    self.log("inject_drop", 0, mid, "n=%d" % n)
                    continue
                if self.fail_resp.get(mid, 0) >= n:
                    with self.lock:
                        rec["state"] = "queued"
                        rec["attempts"] = n
                        rec["last_send_ns"] = now_ns
                        rec["fail_send"] += 1
                        rec["sends"].append({"n": n, "t_ns": now_ns, "ack": "none",
                                             "sendp_us": 0.0, "injected": "fail"})
                        self.stats["send_err_retry"] += 1
                        self.attempts_ever += 1
                        rec["item"] = self._new_item(mid, rec["item"].t0_ns)
                        self.sched.enqueue(rec["item"])
                    self.log("inject_fail", 0, mid, "n=%d" % n)
                    continue
                try:
                    nbytes, sendp_us = self.send(ETH_AI, 0, mid, KIND_RESP,
                                                 item.t0_ns,
                                                 b"\x00" * (item.nbytes - 20),
                                                 flags=n)
                except Exception as exc:
                    with self.lock:
                        rec["state"] = "queued"
                        self.stats["send_err_retry"] += 1
                        rec["item"] = self._new_item(mid, rec["item"].t0_ns)
                        self.sched.enqueue(rec["item"])
                    self.log("send_err", 0, mid, str(exc))
                    continue
                with self.lock:
                    rec["state"] = "inflight"
                    rec["attempts"] = n
                    rec["last_ns"] = time.monotonic_ns()
                    rec["last_send_ns"] = now_ns
                    rec["sends"].append({"n": n, "t_ns": now_ns, "ack": "none",
                                         "sendp_us": sendp_us})
                    self.stats["responses_sent"] += 1
                    self.stats["sendp_calls"] += 1
                    self.attempts_ever += 1
                    self.sched.note_served(item)

    # ---------- retransmit ----------
    def retx_loop(self):
        while not self.stop:
            now = time.monotonic_ns()
            retry = []
            with self.lock:
                for mid, rec in self.records.items():
                    if rec["state"] == "rejected":
                        # admission event: retry quickly (event-driven), not on
                        # the inflight timeout. Bounded by reject_retries.
                        if (now - rec["recv_ns"]) / 1e6 > self.a.deadline_ms:
                            rec["state"] = "abandoned"
                            self.stats["abandoned"] += 1
                            self.log("abandoned", 0, mid, "deadline")
                            continue
                        if (now - rec.get("reject_ns", now)) / 1e6 >= self.a.reject_retry_ms:
                            self.stats["retry_rejected"] += 1
                            rec["item"] = self._new_item(mid, rec["item"].t0_ns)
                            retry.append(mid)
                        continue
                    if rec["state"] != "inflight":
                        continue
                    if rec["attempts"] >= self.a.max_resend + 1:
                        rec["state"] = "abandoned"
                        self.stats["abandoned"] += 1
                        self.log("abandoned", 0, mid, "attempts=%d" % rec["attempts"])
                        continue
                    if (now - rec["last_ns"]) / 1e6 >= self.a.resp_timeout_ms:
                        for s in reversed(rec["sends"]):
                            if s["ack"] == "none":
                                s["ack"] = "timeout"
                                break
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
                          filter="ether proto 0x88b6 or ether proto 0x88b8 or ether proto 0x88b9",
                          prn=self.on_frame, store=0)
        sn.start()
        ts = [threading.Thread(target=f, daemon=True)
              for f in (self.ack_loop, self.gen_loop,
                        self.tx_loop, self.retx_loop)]
        for t in ts:
            t.start()
        time.sleep(self.a.seconds)
        self.stop = True
        time.sleep(0.3)
        try:
            sn.stop()
        except Exception:
            pass
        res = {"role": "server", "mode": self.a.mode, "pacing": self.a.pacing,
               "rate_mbps": self.a.rate_mbps, "bulk_mbps": self.a.bulk_mbps,
               "unique_requests": self.created_total}
        with self.lock:
            res.update(self.stats)
            res.update(self.sched.stats())
            # message-level terminal states (not per-ACK counts)
            states = collections.Counter(r["state"] for r in self.records.values())
            res["msg_done"] = states.get("done", 0)
            res["msg_abandoned"] = states.get("abandoned", 0)
            res["msg_rejected"] = states.get("rejected", 0)
            res["attempts_total"] = self.attempts_ever
            res["attempts_ledger"] = sum(len(r["sends"]) for r in self.records.values())
            res["attempts_ge_sendp"] = self.attempts_ever >= self.stats["sendp_calls"]
            if self.tx is not None:
                res["fast_tx"] = True
                res["tx_frames"] = self.tx.frames
                res["tx_errors"] = self.tx.errors
        if self.a.ledger:
            with open(self.a.ledger, "w", encoding="utf-8") as fh:
                for mid, rec in self.records.items():
                    fh.write(json.dumps({
                        "mid": mid, "t_recv_ns": rec["recv_ns"],
                        "constructed": rec["constructed"],
                        "dup_requests": rec["dup_requests"],
                        "injected_drop": rec["injected_drop"],
                        "attempts": rec["attempts"],
                        "deadline_ns": rec["recv_ns"] + int(self.a.deadline_ms * 1e6),
                        "sends": rec["sends"], "final": rec["state"]},
                        ensure_ascii=False) + "\n")
        return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fifo", "quota", "ai-first", "both"], default="fifo")
    ap.add_argument("--ip", default="192.168.240.2")
    ap.add_argument("--src-mac", default="40:c2:ba:52:70:95")
    ap.add_argument("--client-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--seconds", type=float, default=14)
    ap.add_argument("--rate-mbps", type=float, default=10.0)
    ap.add_argument("--fast-tx", dest="fast_tx", action="store_true", default=False,
                    help="send via Npcap pcap_sendpacket instead of scapy sendp")
    ap.add_argument("--pacing", dest="pacing", action="store_true", default=True)
    ap.add_argument("--no-pacing", dest="pacing", action="store_false")
    ap.add_argument("--bulk-mbps", type=float, default=0.0)
    ap.add_argument("--bulk-delay", type=float, default=0.0)
    ap.add_argument("--flows", type=int, default=4)
    ap.add_argument("--capacity", type=int, default=200)
    ap.add_argument("--min-per-flow", type=int, default=20)
    ap.add_argument("--response-bytes", type=int, default=1200)
    ap.add_argument("--send-batch", type=int, default=8)
    ap.add_argument("--resp-timeout-ms", type=float, default=80.0)
    ap.add_argument("--reject-retry-ms", type=float, default=5.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--drop-resp", default="", help='e.g. "1001:1,1002:2"')
    ap.add_argument("--fail-resp", default="", help='e.g. "1003:1"')
    ap.add_argument("--drop-ack-req", default="", help='e.g. "1004:2"')
    ap.add_argument("--buffer-depth", type=int, default=64)
    ap.add_argument("--deadline-ms", type=float, default=30000.0)
    ap.add_argument("--ledger", default="")
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


















