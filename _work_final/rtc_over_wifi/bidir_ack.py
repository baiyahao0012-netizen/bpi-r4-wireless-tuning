from scapy.all import sniff, Ether
iface=r"\Device\NPF_{C33D086D-AA6B-4D75-8D9F-03881CC0B98D}"
def cb(p):
    if p.haslayer(Ether) and p[Ether].type==0x88b5:
        raw=bytes(p); pl=raw[14:]
        if pl.startswith(b"ACK_FROM_AP"): print("ACK",p.summary())
sniff(iface=iface, timeout=10, prn=cb, store=False)
