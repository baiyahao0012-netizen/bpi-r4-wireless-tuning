from scapy.all import sniff, Ether
import struct, time, hashlib
iface=r"\Device\NPF_{979E392E-3BC0-4097-AA08-5F57FAAAE99A}"
chunks={}; ts={}; first=None; last=None
def cb(p):
    global first,last
    try:
        if Ether not in p or p[Ether].type != 0x88b5: return
        pl=bytes(p)[14:]
        if len(pl)<16: return
        magic,seq,ln,flags,rv=struct.unpack("!IIHHI",pl[:16])
        if magic!=0x52544331: return
        if first is None: first=time.time()
        last=time.time()
        chunks[seq]=pl[16:16+ln]; ts[seq]=rv
    except Exception: pass
sniff(iface=iface, timeout=12, prn=cb, store=False)
print("chunks",len(chunks),"max",max(chunks) if chunks else -1,"span",round(last-first,3) if first else 0)
if chunks:
    mx=max(chunks); out=bytearray(); miss=0
    for i in range(mx+1):
        if i in chunks: out+=chunks[i]
        else: miss+=1
    open(r"C:\Temp\recv_live.h264","wb").write(out)
    print("missing",miss,"bytes",len(out),"sha",hashlib.sha256(out).hexdigest()[:16])
