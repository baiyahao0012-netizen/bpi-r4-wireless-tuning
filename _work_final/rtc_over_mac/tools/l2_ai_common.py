#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared L2 AI demo protocol: 12-byte RTC shim + AI record header.

Reuses the shim layout already used by tools/rate_send.py (!BBHHBBHH) so the
frames stay compatible with the existing L2 tooling.

EtherTypes:
  0x88B6  AI text (request client->server, response server->client)
  0x88B7  bulk traffic (client->server) to contend in the same queue
  0x88B8  AI ack (one per delivered AI record, any direction)
"""
import binascii
import struct

ETH_AI = 0x88B6
ETH_BULK = 0x88B7
ETH_ACK = 0x88B8
ETH_ECHO = 0x88B9   # L2 echo probe (single-clock RTT floor)

SHIM = struct.Struct("!BBHHBBHH")      # ver,type,flow,len,ttl,hlen,crc,stream
AIHDR = struct.Struct("!IHHQI")        # msg_id, kind, plen, t0_ns, flags

KIND_REQ = 0
KIND_RESP = 1
KIND_BULK = 2


def build_frame(dst_mac, src_mac, ethertype, flow, msg_id, kind, t0_ns,
                payload=b"", flags=0, stream=0):
    """Return the full Ethernet frame bytes."""
    body = AIHDR.pack(msg_id & 0xFFFFFFFF, kind, len(payload), t0_ns & 0xFFFFFFFFFFFFFFFF, flags) + payload
    shim = SHIM.pack(0x11, 0, flow & 0xFFFF, len(body), 8, 12, 0, stream)
    crc = binascii.crc_hqx(shim + body, 0)
    shim = SHIM.pack(0x11, 0, flow & 0xFFFF, len(body), 8, 12, crc, stream)
    return dst_mac + src_mac + struct.pack("!H", ethertype) + shim + body


def parse_frame(raw):
    """Return dict or None. raw includes the Ethernet header."""
    if len(raw) < 14 + SHIM.size + AIHDR.size:
        return None
    ethertype = struct.unpack("!H", raw[12:14])[0]
    if ethertype not in (ETH_AI, ETH_BULK, ETH_ACK, ETH_ECHO):
        return None
    shim = raw[14:14 + SHIM.size]
    ver, typ, flow, plen, ttl, hlen, crc, stream = SHIM.unpack(shim)
    body = raw[14 + SHIM.size:]
    if plen > len(body):
        return None
    body = body[:plen]
    shim_zero = struct.pack("!BBHHBBHH", ver, typ, flow, plen, ttl, hlen, 0, stream)
    if binascii.crc_hqx(shim_zero + body, 0) != crc:
        return None
    msg_id, kind, paylen, t0_ns, flags = AIHDR.unpack(body[:AIHDR.size])
    return {
        "ethertype": ethertype,
        "flow": flow,
        "msg_id": msg_id,
        "kind": kind,
        "t0_ns": t0_ns,
        "flags": flags,
        "payload": body[AIHDR.size:AIHDR.size + paylen],
        "dst": raw[0:6],
        "src": raw[6:12],
    }


def mac_bytes(s):
    return bytes.fromhex(s.replace(":", "").replace("-", ""))


def mac_str(b):
    return ":".join("%02x" % x for x in b)

