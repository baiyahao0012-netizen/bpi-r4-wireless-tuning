#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 AI server (Windows, scapy + Npcap, must run elevated).

Receives AI requests over 0x88B6, dedups by msg_id (so a retransmitted request
triggers exactly one response), answers with a response record and an ACK, and
keeps a small outstanding table for its own responses (ACK timeout -> resend,
max N). Bulk frames on 0x88B7 are only counted.
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

from scapy.all import AsyncSniffer, Ether, Raw, conf, sendp


class Server:
    def __init__(self, a, iface):
        self.a = a
        self.iface = iface
        self.src = mac_bytes(a.src_mac)
        self.dst = mac_bytes(a.client_mac)
        self.seen = set()
        self.bulk_rx = 0
        self.req_rx = 0
        self.req_dup = 0
        self.resp_sent = 0
        self.resp_acked = 0
        self.resp_resend = 0
        self.ack_dropped = 0
        self.resp_dropped = 0
        self.outstanding = {}     # msg_id -> dict(attempts, last_ns)
        self.lock = threading.Lock()
        self.stop = False

    def send(self, ethertype, flow, msg_id, kind, t0_ns, payload=b""):
        frame = build_frame(self.dst, self.src, ethertype, flow, msg_id, kind,
                            t0_ns, payload)
        sendp(Ether(dst=self.dst, src=self.src, type=ethertype) / Raw(frame[14:]),
              iface=self.iface, verbose=0)

    def on_frame(self, pkt):
        p = parse_frame(bytes(pkt))
        if not p:
            return
        if p["src"] == self.src:
            return  # our own outgoing frame
        if p["ethertype"] == ETH_BULK:
            self.bulk_rx += 1
            return
        if p["ethertype"] == ETH_ACK:
            with self.lock:
                self.outstanding.pop(p["msg_id"], None)
                self.resp_acked += 1
            return
        if p["ethertype"] == ETH_AI and p["kind"] == KIND_REQ:
            self.req_rx += 1
            mid = p["msg_id"]
            with self.lock:
                dup = mid in self.seen
                self.seen.add(mid)
            if dup:
                self.req_dup += 1
            else:
                # one inference per request id: answer + ack
                if random.random() >= self.a.resp_drop:
                    self.send(ETH_AI, 0, mid, KIND_RESP, p["t0_ns"], b"R%08d" % mid)
                    self.resp_sent += 1
                else:
                    self.resp_dropped += 1
                with self.lock:
                    self.outstanding[mid] = {"attempts": 1, "last_ns": time.monotonic_ns()}
            # ack the request either way (idempotent); may be lost on purpose
            if random.random() >= self.a.ack_drop:
                self.send(ETH_ACK, 0, mid, 3, 0, struct.pack("!I", 0))
            else:
                self.ack_dropped += 1

    def retx_loop(self):
        while not self.stop:
            now = time.monotonic_ns()
            for mid, rec in list(self.outstanding.items()):
                if rec["attempts"] > self.a.max_resend:
                    continue
                if (now - rec["last_ns"]) / 1e6 >= self.a.ack_timeout_ms:
                    rec["attempts"] += 1
                    rec["last_ns"] = now
                    self.send(ETH_AI, 0, mid, KIND_RESP, 0, b"R%08d" % mid)
                    self.resp_resend += 1
            time.sleep(0.01)

    def run(self):
        sn = AsyncSniffer(iface=self.iface,
                          filter="ether proto 0x88b6 or ether proto 0x88b7 or ether proto 0x88b8",
                          prn=self.on_frame, store=0)
        sn.start()
        th = threading.Thread(target=self.retx_loop, daemon=True)
        th.start()
        time.sleep(self.a.seconds)
        self.stop = True
        try:
            sn.stop()
        except Exception:
            pass
        return {
            "role": "server",
            "requests_rx": self.req_rx,
            "requests_dup": self.req_dup,
            "responses_sent": self.resp_sent,
            "responses_acked": self.resp_acked,
            "responses_resent": self.resp_resend,
            "bulk_rx": self.bulk_rx,
            "dedup_ok": self.req_dup >= 0,
            "ack_dropped": self.ack_dropped,
            "resp_dropped": self.resp_dropped,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="192.168.240.2")
    ap.add_argument("--src-mac", default="40:c2:ba:52:70:95")
    ap.add_argument("--client-mac", default="90:de:80:1c:6a:7a")
    ap.add_argument("--seconds", type=float, default=22)
    ap.add_argument("--ack-timeout-ms", type=float, default=50.0)
    ap.add_argument("--max-resend", type=int, default=8)
    ap.add_argument("--ack-drop", type=float, default=0.0)
    ap.add_argument("--resp-drop", type=float, default=0.0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    from scapy.arch import get_if_addr
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
    s = Server(a, dev)
    res = s.run()
    text = "RESULT " + json.dumps(res, ensure_ascii=False)
    print(text, flush=True)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()



