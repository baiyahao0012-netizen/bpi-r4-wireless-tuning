#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scheduler policies shared by the demo roles.

Mirrors contrib/genai (ns3-agent-dev_l2):
  quota   -> QuotaWifiQueueScheduler::HasToDropBeforeEnqueue
             share = max(MinPerFlow*1484, capacity*1484/n_active_flows)
             evict the oldest frame of the flow most over its share,
             otherwise refuse the arriving frame; service order stays FCFS.
  ai-first-> AiFirstWifiQueueScheduler::GetPriority
             AI rank 0, others rank 1, FCFS within a class; no enqueue eviction.
"""
import collections


class Item:
    __slots__ = ("flow", "msg_id", "kind", "t0_ns", "nbytes", "enq_ns", "attempt")

    def __init__(self, flow, msg_id, kind, t0_ns, nbytes, attempt=0):
        import time
        self.flow = flow
        self.msg_id = msg_id
        self.kind = kind
        self.t0_ns = t0_ns
        self.nbytes = nbytes
        self.enq_ns = time.monotonic_ns()
        self.attempt = attempt


class Scheduler:
    def __init__(self, mode, capacity, min_per_flow, log):
        self.mode = mode
        self.capacity = capacity
        self.min_per_flow = min_per_flow
        self.log = log
        self.queues = collections.OrderedDict()
        self.npackets = 0
        self.nbytes = 0
        self.max_depth = 0
        self.evictions = 0
        self.rejections = 0
        self.dropped = collections.Counter()
        self.served = []          # 服务序列（用于机制级判据）

    def _plain(self, item):
        self.queues.setdefault(item.flow, collections.deque()).append(item)
        self.npackets += 1
        self.nbytes += item.nbytes
        self.max_depth = max(self.max_depth, self.npackets)

    def enqueue(self, item):
        full = self.npackets >= self.capacity
        if full and self.mode in ("quota", "both"):
            nflows = max(1, len(self.queues))
            share = max(self.min_per_flow * 1484, self.capacity * 1484 // nflows)
            own = sum(i.nbytes for i in self.queues.get(item.flow, ()))
            if own < share:
                victim = self._pick_victim(share)
                if victim is not None:
                    vq = self.queues[victim.flow]
                    v = vq.popleft()
                    self.npackets -= 1
                    self.nbytes -= v.nbytes
                    self.evictions += 1
                    self.dropped[victim.flow] += 1
                    self.log("evict", v.flow, v.msg_id, "quota_evict")
                    full = False
            if full:
                self.rejections += 1
                self.dropped[item.flow] += 1
                self.log("reject", item.flow, item.msg_id, "quota_reject")
                return False
        elif full:
            self.rejections += 1
            self.dropped[item.flow] += 1
            self.log("reject", item.flow, item.msg_id, "queue_full")
            return False
        self._plain(item)
        return True

    def _pick_victim(self, share):
        best, best_over = None, None
        for flow, q in self.queues.items():
            if not q:
                continue
            over = sum(i.nbytes for i in q) - share
            if over > 0 and (best_over is None or over > best_over):
                best, best_over = q[0], over
        return best

    def pop(self):
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
        self.served.append((item.flow, item.kind))
        return item

    def stats(self):
        return {
            "evictions": self.evictions,
            "rejections": self.rejections,
            "max_queue_depth": self.max_depth,
            "drops_by_flow": dict(self.dropped),
        }
