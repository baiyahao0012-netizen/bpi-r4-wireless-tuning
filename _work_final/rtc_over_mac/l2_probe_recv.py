#!/usr/bin/env python3
"""Capture custom EtherType 0x88B5 frames on the laptop Ethernet with Npcap."""
import sys
from scapy.all import Ether, sniff

TARGET_MAC = "40:c2:ba:52:70:95"
count = 0


def cb(pkt):
    global count
    if Ether in pkt and pkt[Ether].type == 0x88B5:
        count += 1
        print("rx", count, pkt[Ether].src, pkt[Ether].dst, len(pkt), flush=True)


IFACE = r"\Device\NPF_{A2958734-FBD5-4E72-AD1C-362588589CD1}"
sniff(iface=IFACE, filter="ether proto 0x88b5", timeout=15, store=False, prn=cb)
print("total", count, flush=True)
