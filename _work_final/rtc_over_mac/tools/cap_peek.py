import sys
import time

from scapy.all import conf, sniff

iface = sys.argv[1]
secs = float(sys.argv[2])
state = {"n": 0, "first": [], "srcs": {}}

conf.bufsize = 64 * 1024 * 1024
conf.use_pcap = True


def cb(p):
    state["n"] += 1
    try:
        s = p.summary()
    except Exception:
        s = "?"
    if len(state["first"]) < 6:
        state["first"].append(s)
    try:
        key = p[0].src if p.haslayer("Ether") else "?"
        state["srcs"][key] = state["srcs"].get(key, 0) + 1
    except Exception:
        pass


sniff(iface=iface, timeout=secs, store=False, prn=cb)
print("total_packets=%d" % state["n"], flush=True)
for k, v in sorted(state["srcs"].items(), key=lambda x: -x[1])[:8]:
    print("src %s -> %d" % (k, v), flush=True)
for s in state["first"]:
    print("first:", s, flush=True)
