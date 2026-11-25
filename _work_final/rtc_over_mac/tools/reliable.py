#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulation-equivalent reliable delivery buffer, shared by both paths.

Mirrors the ns-3 side semantics:
  - store before send            (add() before the first transmit)
  - per-chunk ACK                (on_ack(), like AckedMpdu)
  - kMaxResendsPerChunk = 8      (max_sends = 9: initial + 8)
  - buffer depth 64              (evict oldest unacked, like AiTextRetransmitBuffer)
  - deadline / expired           (attempts exhausted -> expired)
  - per-chunk ledger             (attempts, acked, expired, evicted)

ACK carries cum_seq + a 32-bit bitmap so per-chunk state stays exact even when
individual ACK frames are lost (bit i == seq cum_seq+1+i received).
"""
import json
import threading
import time


class ReliableBuffer:
    def __init__(self, depth=64, rto_ms=400.0, max_sends=9,
                 on_send=None, ledger_path=None):
        self.depth = depth
        self.rto = rto_ms / 1000.0
        self.max_sends = max_sends
        self.on_send = on_send
        self.lock = threading.RLock()
        self.chunks = {}          # (qid, seq) -> dict
        self.order = []           # insertion order for eviction
        self.stats = {"sent": 0, "acked": 0, "retx": 0, "expired": 0,
                      "evicted": 0, "dup_ack": 0}
        self.ledger = open(ledger_path, "a", buffering=1,
                           encoding="utf-8") if ledger_path else None

    def add(self, qid, seq, frame):
        now = time.monotonic_ns()
        with self.lock:
            key = (qid, seq)
            if key in self.chunks:
                return
            if len(self.order) >= self.depth:
                old = self.order.pop(0)
                self.chunks.pop(old, None)
                self.stats["evicted"] += 1
                self._log({"event": "evicted", "qid": old[0], "seq": old[1]})
            self.chunks[key] = {"frame": frame, "sends": 0, "first": now,
                                "last": 0, "acked": False}
            self.order.append(key)
        self._send(key)

    def _send(self, key):
        with self.lock:
            rec = self.chunks.get(key)
            if rec is None:
                return False
            rec["sends"] += 1
            rec["last"] = time.monotonic_ns()
            self.stats["sent"] += 1
            frame = rec["frame"]
        if self.on_send:
            try:
                self.on_send(frame)
            except Exception:
                pass
        return True

    def on_ack(self, qid, cum, bitmap):
        with self.lock:
            for key in list(self.chunks.keys()):
                if key[0] != qid:
                    continue
                seq = key[1]
                ok = seq < cum or (cum <= seq < cum + 32 and
                                    (bitmap >> (seq - cum)) & 1)
                if not ok:
                    continue
                rec = self.chunks.pop(key)
                self.order.remove(key)
                if rec["acked"]:
                    self.stats["dup_ack"] += 1
                rec["acked"] = True
                self.stats["acked"] += 1
                self._log({"event": "acked", "qid": qid, "seq": seq,
                           "attempts": rec["sends"],
                           "rtt_ms": round((time.monotonic_ns() - rec["first"]) / 1e6, 1)})

    def tick(self):
        """Return frames to resend; expire chunks past max_sends."""
        now = time.monotonic_ns()
        out = []
        with self.lock:
            for key in list(self.order):
                rec = self.chunks.get(key)
                if rec is None:
                    continue
                if now - rec["last"] < self.rto * 1e9:
                    continue
                if rec["sends"] >= self.max_sends:
                    self.chunks.pop(key, None)
                    self.order.remove(key)
                    self.stats["expired"] += 1
                    self._log({"event": "expired", "qid": key[0], "seq": key[1],
                               "attempts": rec["sends"]})
                    continue
                self.stats["retx"] += 1
                out.append(key)
        for key in out:
            self._send(key)
        return [self.chunks[k]["frame"] for k in out if k in self.chunks]

    def clear(self):
        with self.lock:
            self.chunks.clear()
            self.order.clear()
            for k in self.stats:
                self.stats[k] = 0

    def pending(self):
        with self.lock:
            return len(self.chunks)

    def _log(self, obj):
        if self.ledger:
            self.ledger.write(json.dumps(obj, ensure_ascii=False) + "\n")
