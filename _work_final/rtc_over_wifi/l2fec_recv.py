from scapy.all import sniff, Ether
import struct, time, hashlib
iface=r"\Device\NPF_{C33D086D-AA6B-4D75-8D9F-03881CC0B98D}"
data={}; parity={}; drop=5
def cb(p):
    try:
        if Ether not in p or p[Ether].type != 0x88b5: return
        pl=bytes(p)[14:]
        if len(pl)<16: return
        magic,seq,ln,flags,gid=struct.unpack("!IIHHI", pl[:16])
        if magic != 0x52544331: return
        payload=pl[16:16+ln]
        if flags & 1:
            parity[gid]=(seq,payload)
        else:
            if seq==drop:
                print("deliberately dropped seq",seq)
            else:
                data[seq]=payload
    except Exception: pass
sniff(iface=iface, timeout=10, prn=cb, store=False)
print("data",len(data),"parity",len(parity))
# recover group 0: seq 0..7 data, parity 8
for gid,(pseq,par) in parity.items():
    base=gid*9
    missing=[base+i for i in range(8) if (base+i) not in data]
    if len(missing)==1:
        rec=bytearray(par)
        for i in range(8):
            s=base+i
            if s in data:
                d=data[s]
                for j in range(len(d)): rec[j]^=d[j]
        data[missing[0]]=bytes(rec)
        print("recovered",missing[0],"len",len(rec))
mx=max(data); out=bytearray(); miss=0
for i in range(mx+1):
    if i in data: out+=data[i]
    else: miss+=1
open(r"C:\Temp\recv_fec.h264","wb").write(out)
print("bytes",len(out),"missing",miss,"sha",hashlib.sha256(out).hexdigest()[:16])
