#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal pcap analyzer for the OAF Doubao A/B captures.
Extracts DSCP distribution (overall + per direction), flow inventory,
TCP SYN RTT and retransmit counts. No third-party deps.
"""
import struct, sys, collections, socket

def read_pcap(path):
    with open(path, 'rb') as f:
        data = f.read()
    magic = struct.unpack('<I', data[:4])[0]
    if magic == 0x0a0d0d0a:
        raise SystemExit('pcapng not supported: %s' % path)
    if magic == 0xa1b2c3d4: endian, nano = '<', False
    elif magic == 0xd4c3b2a1: endian, nano = '>', False
    elif magic == 0xa1b23c4d: endian, nano = '<', True
    elif magic == 0x4d3cb2a1: endian, nano = '>', True
    else: raise SystemExit('unknown magic %08x in %s' % (magic, path))
    linktype = struct.unpack(endian + 'I', data[20:24])[0]
    recs, off, n = [], 24, len(data)
    while off + 16 <= n:
        ts_s, ts_us, incl, orig = struct.unpack(endian + 'IIII', data[off:off+16])
        off += 16
        pkt = data[off:off+incl]; off += incl
        recs.append((ts_s + (ts_us / 1e9 if nano else ts_us / 1e6), pkt))
    return linktype, recs

def l3_offset(linktype, pkt):
    if linktype == 1:
        if len(pkt) < 14: return None
        et = struct.unpack('!H', pkt[12:14])[0]; o = 14
        if et == 0x8100: o += 4; et = struct.unpack('!H', pkt[o-2:o])[0]
        elif et == 0x88a8: o += 8
        return o if et == 0x0800 else None
    if linktype == 113:
        return 16 if len(pkt) >= 16 and struct.unpack('!H', pkt[14:16])[0] == 0x0800 else None
    if linktype == 276:
        return 20 if len(pkt) >= 20 and struct.unpack('!H', pkt[0:2])[0] == 0x0800 else None
    if linktype == 101: return 0
    return None

def parse_ip(pkt, o):
    if o is None or len(pkt) < o + 20: return None
    b = pkt[o]
    if (b >> 4) != 4: return None
    ihl = (b & 0x0f) * 4
    if ihl < 20 or len(pkt) < o + ihl: return None
    tos = pkt[o+1]
    total = struct.unpack('!H', pkt[o+2:o+4])[0]
    proto = pkt[o+9]
    src = socket.inet_ntoa(pkt[o+12:o+16]); dst = socket.inet_ntoa(pkt[o+16:o+20])
    end = o + (total if 0 < total <= len(pkt)-o else len(pkt)-o)
    return dict(tos=tos, dscp=tos >> 2, proto=proto, src=src, dst=dst, payload=pkt[o+ihl:end])

def parse_tcp(pl):
    if len(pl) < 20: return None
    sp, dp, seq, ack = struct.unpack('!HHII', pl[:12])
    off = (pl[12] >> 4) * 4; flags = pl[13]
    return dict(sp=sp, dp=dp, seq=seq, ack=ack, flags=flags, hlen=off,
                syn=bool(flags & 0x02), ack_f=bool(flags & 0x10))

DSCP_NAMES = {0:'CS0/BE', 8:'CS1', 24:'CS3', 34:'AF41', 40:'CS5', 46:'EF', 48:'CS6'}

def analyze(path):
    lt, recs = read_pcap(path)
    dscp_hist = collections.Counter(); dscp_bytes = collections.Counter()
    flows = collections.Counter(); proto_hist = collections.Counter()
    syn_pairs = {}; syn_rtt = []; seen_seq = set(); retrans = 0; tcp_pkts = 0
    total = 0; first_ts = last_ts = None
    per_ip = collections.Counter()
    dl = dict(pkts=0, bytes=0, ef_pkts=0, ef_bytes=0, dscp=collections.Counter(), bytes_by_dscp=collections.Counter(), remote=collections.Counter(), remote_ef=collections.Counter())
    ul = dict(pkts=0, bytes=0, ef_pkts=0, ef_bytes=0, dscp=collections.Counter(), bytes_by_dscp=collections.Counter(), remote=collections.Counter(), remote_ef=collections.Counter())
    parsed = []
    for ts, pkt in recs:
        if first_ts is None: first_ts = ts
        last_ts = ts; total += 1
        ip = parse_ip(pkt, l3_offset(lt, pkt))
        if not ip: continue
        parsed.append((ts, ip))
        dscp_hist[ip['dscp']] += 1; dscp_bytes[ip['dscp']] += len(pkt)
        proto_hist[ip['proto']] += 1
        per_ip[ip['src']] += 1; per_ip[ip['dst']] += 1
        flows[(ip['src'], ip['dst'], ip['proto'])] += 1
        if ip['proto'] == 6:
            t = parse_tcp(ip['payload'])
            if not t: continue
            tcp_pkts += 1
            fk = (ip['src'], t['sp'], ip['dst'], t['dp'])
            if t['syn'] and not t['ack_f']: syn_pairs[fk] = (ts, t['seq'])
            elif t['syn'] and t['ack_f']:
                rev = (ip['dst'], t['dp'], ip['src'], t['sp'])
                if rev in syn_pairs:
                    t0, _ = syn_pairs.pop(rev); syn_rtt.append((ts - t0) * 1000.0)
            plen = len(ip['payload']) - t['hlen']
            if plen > 0:
                s = (fk, t['seq'])
                if s in seen_seq: retrans += 1
                else: seen_seq.add(s)
    # identify STA: private 192.168.240.x endpoint with most packets
    priv = [ip for ip, c in per_ip.items() if ip.startswith('192.168.240.') and ip != '192.168.240.1']
    sta = max(priv, key=lambda ip: per_ip[ip]) if priv else None
    for ts, ip in parsed:
        side = dl if ip['dst'] == sta else (ul if ip['src'] == sta else None)
        if side is None: continue
        nb = len(ip['payload']) + 20
        side['pkts'] += 1; side['bytes'] += nb
        side['dscp'][ip['dscp']] += 1; side['bytes_by_dscp'][ip['dscp']] += nb
        remote = ip['src'] if ip['dst'] == sta else ip['dst']
        side['remote'][remote] += 1
        if ip['dscp'] == 46:
            side['ef_pkts'] += 1; side['ef_bytes'] += nb; side['remote_ef'][remote] += 1
    dur = (last_ts - first_ts) if (first_ts and last_ts) else 0
    return dict(path=path, linktype=lt, packets=total, duration=dur, dscp_hist=dscp_hist,
                dscp_bytes=dscp_bytes, proto_hist=proto_hist, flows=flows, syn_rtt=syn_rtt,
                retrans=retrans, tcp_pkts=tcp_pkts, sta=sta, dl=dl, ul=ul)

def pct(v, n): return '%.1f%%' % (100.0*v/n) if n else 'n/a'

def report(r):
    print('=' * 74)
    print('FILE      :', r['path'])
    print('linktype  :', r['linktype'], '| packets:', r['packets'], '| duration: %.1f s' % r['duration'], '| STA:', r['sta'])
    print('proto     :', dict(r['proto_hist']), '| TCP pkts:', r['tcp_pkts'], '| dup-seq retrans:', r['retrans'])
    d, db = r['dscp_hist'], r['dscp_bytes']; tb = sum(db.values())
    print('DSCP overall (pkts / bytes):')
    for k in sorted(d, key=lambda x: -db[x]):
        print('   %-7s dscp=%-3d pkts=%-6d %-7s bytes=%-9d %s' % (DSCP_NAMES.get(k,'?'), k, d[k], pct(d[k], r['packets']), db[k], pct(db[k], tb)))
    sr = sorted(r['syn_rtt'])
    if sr:
        q = lambda p: sr[min(len(sr)-1, int(p*(len(sr)-1)))]
        print('SYN RTT ms: n=%d min=%.1f p50=%.1f p95=%.1f max=%.1f' % (len(sr), sr[0], q(0.5), q(0.95), sr[-1]))
    for label, side in (('DOWNLINK (to STA)', r['dl']), ('UPLINK (from STA)', r['ul'])):
        print('%s: pkts=%d bytes=%d | EF pkts=%d (%s) EF bytes=%d (%s)' % (
            label, side['pkts'], side['bytes'], side['ef_pkts'], pct(side['ef_pkts'], side['pkts']),
            side['ef_bytes'], pct(side['ef_bytes'], side['bytes'])))
        print('   dscp bytes:', {DSCP_NAMES.get(k,k): side['bytes_by_dscp'][k] for k in sorted(side['bytes_by_dscp'], key=lambda x: -side['bytes_by_dscp'][x])})
        top = side['remote'].most_common(6)
        for rip, c in top:
            print('   remote %-16s pkts=%-5d EF_pkts=%d' % (rip, c, side['remote_ef'].get(rip, 0)))

if __name__ == '__main__':
    for p in sys.argv[1:]:
        report(analyze(p))
