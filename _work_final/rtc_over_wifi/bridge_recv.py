from scapy.all import sniff, Ether
iface=r"\Device\NPF_{979E392E-3BC0-4097-AA08-5F57FAAAE99A}"
pkts=sniff(iface=iface, timeout=10, lfilter=lambda p: p.haslayer(Ether) and p[Ether].type==0x88b5, store=True)
print("bridge_captured",len(pkts))
for p in pkts:
    print(p.summary())
    print(bytes(p)[:60])
