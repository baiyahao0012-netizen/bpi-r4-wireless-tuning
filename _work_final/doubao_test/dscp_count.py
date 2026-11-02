# -*- coding: utf-8 -*-
import sys, collections
from scapy.all import PcapReader, IP
path = sys.argv[1]
c = collections.Counter(); down = collections.Counter(); up = collections.Counter()
PHONE = "192.168.240.219"
for pkt in PcapReader(path):
    if IP not in pkt: continue
    ip = pkt[IP]
    d = int(ip.tos) >> 2
    c[d] += 1
    if ip.dst == PHONE: down[d] += 1
    elif ip.src == PHONE: up[d] += 1
print("DSCP all:", dict(sorted(c.items())))
print("DSCP downlink:", dict(sorted(down.items())))
print("DSCP uplink:", dict(sorted(up.items())))
