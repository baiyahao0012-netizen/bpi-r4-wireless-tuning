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
import time


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
        self.evicted_by_flow = collections.Counter()
        self.rejected_by_flow = collections.Counter()
        self.ai_overtakes = 0
        self.fcfs_violations = 0
        self.service_order = collections.deque(maxlen=256)
        self.served = []          # 閺堝秴濮熸惔蹇撳灙閿涘牏鏁ゆ禍搴㈡簚閸掑墎楠囬崚銈嗗祦閿?
    def push_front(self, item):
        """Return an unserved item to the head of its flow queue (token shortage)."""
        self.queues.setdefault(item.flow, collections.deque()).appendleft(item)
        self.npackets += 1
        self.nbytes += item.nbytes

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
                    self.evicted_by_flow[victim.flow] += 1
                    self.log("evict", v.flow, v.msg_id, "quota_evict")
                    full = False
            if full:
                self.rejections += 1
                self.dropped[item.flow] += 1
                self.rejected_by_flow[item.flow] += 1
                self.log("reject", item.flow, item.msg_id, "quota_reject")
                return False
        elif full:
            self.rejections += 1
            self.dropped[item.flow] += 1
            self.rejected_by_flow[item.flow] += 1
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

    def _select(self):
        ai_mode = self.mode in ("ai-first", "both")
        if ai_mode and self.queues.get(0):
            return self.queues[0]
        oldest = None
        q = None
        for flow in self.queues:
            cand = self.queues[flow]
            if not cand:
                continue
            if oldest is None or cand[0].enq_ns < oldest:
                oldest = cand[0].enq_ns
                q = cand
        return q

    def peek(self):
        q = self._select()
        return q[0] if q else None

    def pop(self):
        ai_mode = self.mode in ("ai-first", "both")
        q = self._select()
        if q is None:
            return None
        item = q.popleft()
        self.npackets -= 1
        self.nbytes -= item.nbytes
        self.served.append((item.flow, item.kind))
        return item

    def note_served(self, item):
        """Called after the item was actually transmitted (not on speculative pop)."""
        if self.mode in ("ai-first", "both") and item.flow == 0:
            # bulk frames queued *earlier* than this AI frame and still waiting
            self.ai_overtakes += sum(
                1 for flow, dq in self.queues.items() if flow != 0
                for it in dq if it.enq_ns < item.enq_ns)
        if self.service_order and self.service_order[-1][1] == item.flow:
            if item.enq_ns < self.service_order[-1][2]:
                self.fcfs_violations += 1
        self.service_order.append((time.monotonic_ns(), item.flow, item.enq_ns))

    def stats(self):
        return {
            "evictions": self.evictions,
            "rejections": self.rejections,
            "max_queue_depth": self.max_depth,
            "drops_by_flow": dict(self.dropped),
            "evicted_by_flow": dict(self.evicted_by_flow),
            "rejected_by_flow": dict(self.rejected_by_flow),
            "ai_overtakes": self.ai_overtakes,
            "fcfs_violations": self.fcfs_violations,
        }




