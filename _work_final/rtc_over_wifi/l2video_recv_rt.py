from scapy.all import sniff, Ether
import struct, time
iface=r"\Device\NPF_{C33D086D-AA6B-4D75-8D9F-03881CC0B98D}"
chunks={}; first=None; last=None
def cb(p):
    global first,last
    try:
        if Ether not in p or p[Ether].type != 0x88b5: return
        raw=bytes(p); pl=raw[14:]
        if len(pl)<16: return
        magic,seq,ln,flags,rsv=struct.unpack("!IIHHI", pl[:16])
        if magic != 0x52544331: return
        if first is None: first=time.time()
        last=time.time()
        chunks[seq]=pl[16:16+ln]
    except Exception: pass
sniff(iface=iface, timeout=10, prn=cb, store=False)
print("chunks",len(chunks),"max",max(chunks) if chunks else -1,"span",round((last-first),3) if first else 0)
if chunks:
    mx=max(chunks); out=bytearray(); missing=0
    for i in range(mx+1):
        if i in chunks: out+=chunks[i]
        else: missing+=1
    open(r"C:\Temp\recv_rt.h264","wb").write(out)
    print("missing",missing,"bytes",len(out))
