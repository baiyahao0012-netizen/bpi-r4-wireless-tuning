#!/usr/bin/env python3
"""Windows-side probe counter using Npcap (scapy sniff).

Counts arrival, gaps, duplicates, CRC errors and one-way transit jitter.
Works for UDP probes and raw L2 0x88B5 probes.
"""
import argparse
import binascii
import socket
import struct
import time

from scapy.all import Raw, UDP, conf, get_if_addr, get_if_list, sniff

MAGIC = b"PRB1"
HDR = struct.Struct("!4sIQI")
SHIM = struct.Struct("!BBHHBBHH")

conf.bufsize = 64 * 1024 * 1024
conf.use_pcap = True
conf.sniff_promisc = False


def pick_iface(want_ip):
    for i in get_if_list():
        try:
            if get_if_addr(i) == want_ip:
                return i
        except Exception:
            continue
    return conf.iface


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["udp", "l2", "rtp"], required=True)
    ap.add_argument("--port", type=int, default=5100)
    ap.add_argument("--ip", default="192.168.240.2")
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--iface", default="")
    a = ap.parse_args()

    iface = a.iface or pick_iface(a.ip)
    st = {"got": 0, "dup": 0, "bad": 0, "ooo": 0, "seen": set(), "base": None,
          "maxrel": -1, "jitter": 0.0, "prev_transit": None, "first": None, "last": None,
          "per_sec": {}, "ts": set()}

    def note(seq, ts_ns):
        now = time.monotonic_ns()
        if st["first"] is None:
            st["first"] = now
        st["last"] = now
        st["got"] += 1
        sec = int((now - st["first"]) / 1e9)
        st["per_sec"][sec] = st["per_sec"].get(sec, 0) + 1
        if seq in st["seen"]:
            st["dup"] += 1
            return
        st["seen"].add(seq)
        if st["base"] is None:
            st["base"] = seq
        rel = (seq - st["base"]) & 0xFFFFFFFF
        if rel < st["maxrel"]:
            st["ooo"] += 1
        elif rel > st["maxrel"]:
            st["maxrel"] = rel
        transit = now - ts_ns
        if st["prev_transit"] is not None:
            d = abs(transit - st["prev_transit"])
            st["jitter"] += (d - st["jitter"]) / 16.0
        st["prev_transit"] = transit

    def handle_udp(pkt):
        try:
            if not pkt.haslayer(UDP) or not pkt.haslayer(Raw):
                return
            body = bytes(pkt[Raw].load)
        except Exception:
            return
        if len(body) < HDR.size:
            st["bad"] += 1
            return
        if body[:4] != MAGIC:
            return
        _, seq, ts_ns, _ = HDR.unpack(body[:HDR.size])
        note(seq, ts_ns)

    def handle_l2(pkt):
        try:
            raw = bytes(pkt.payload)
        except Exception:
            return
        if len(raw) < SHIM.size:
            st["bad"] += 1
            return
        ver_type, flags, flow, plen, ttl, hlen, crc, stream = SHIM.unpack(raw[:SHIM.size])
        if (ver_type >> 4) != 1 or hlen != SHIM.size or len(raw) < hlen + plen:
            st["bad"] += 1
            return
        body = raw[hlen:hlen + plen]
        chk = bytearray(raw[:SHIM.size])
        chk[8:10] = b"\x00\x00"
        if binascii.crc_hqx(bytes(chk) + body, 0) != crc:
            st["bad"] += 1
            return
        if len(body) < HDR.size or body[:4] != MAGIC:
            st["bad"] += 1
            return
        _, seq, ts_ns, _ = HDR.unpack(body[:HDR.size])
        note(seq, ts_ns)

    def handle_rtp(pkt):
        try:
            raw = bytes(pkt.payload)
        except Exception:
            return
        if len(raw) < SHIM.size:
            st["bad"] += 1
            return
        ver_type, flags, flow, plen, ttl, hlen, crc, stream = SHIM.unpack(raw[:SHIM.size])
        if (ver_type >> 4) != 1 or hlen != SHIM.size or len(raw) < hlen + plen:
            st["bad"] += 1
            return
        body = raw[hlen:hlen + plen]
        chk = bytearray(raw[:SHIM.size])
        chk[8:10] = b"\x00\x00"
        if binascii.crc_hqx(bytes(chk) + body, 0) != crc:
            st["bad"] += 1
            return
        if len(body) < 12 or (body[0] >> 6) != 2:
            st["bad"] += 1
            return
        seq = (body[2] << 8) | body[3]
        ts = (body[4] << 24) | (body[5] << 16) | (body[6] << 8) | body[7]
        st["ts"].add(ts)
        if seq in st["seen"]:
            st["dup"] += 1
            st["got"] += 1
            return
        st["got"] += 1
        st["seen"].add(seq)
        if st["base"] is None:
            st["base"] = seq
        rel = (seq - st["base"]) & 0xFFFF
        st["ts_first"] = st.get("ts_first", ts)
        st["ts_last"] = ts
        if st["maxrel"] < 0:
            st["maxrel"] = rel
        elif rel > st["maxrel"]:
            st["maxrel"] = rel
        else:
            st["ooo"] += 1

    if a.mode == "udp":
        filt, fn = "udp and dst port %d" % a.port, handle_udp
    elif a.mode == "rtp":
        filt, fn = "ether proto 0x88b5", handle_rtp
    else:
        filt, fn = "ether proto 0x88b5", handle_l2
    t0 = time.monotonic()
    sniff(iface=iface, filter=filt, timeout=a.seconds, store=False, prn=fn)
    el = time.monotonic() - t0

    expected = st["maxrel"] + 1 if st["base"] is not None else 0
    loss = (expected - len(st["seen"])) if expected else 0
    span = (st["last"] - st["first"]) / 1e9 if st["first"] else el
    print(
        "mode=%s iface=%s got=%d unique=%d expected=%d missing=%d loss=%.3f%% dup=%d bad=%d ooo=%d "
        "pps=%.0f jitter_rfc=%.2fms window=%.2fs"
        % (a.mode, iface, st["got"], len(st["seen"]), expected, loss,
           100.0 * loss / expected if expected else 0.0, st["dup"], st["bad"], st["ooo"],
           st["got"] / max(span, 1e-9), st["jitter"] / 1e6, span),
        flush=True,
    )
    secs = sorted(st["per_sec"].items())
    if secs:
        print("per_sec=" + " ".join("%d:%d" % (k, v) for k, v in secs), flush=True)
    if a.mode == "rtp":
        print("rtp_unique_ts=%d ts_first=%d ts_last=%d" % (len(st["ts"]), st.get("ts_first", -1), st.get("ts_last", -1)), flush=True)


if __name__ == "__main__":
    main()
