from scapy.all import sniff, Ether, Raw, sendp
import struct, time, hashlib
iface=r"\Device\NPF_{C33D086D-AA6B-4D75-8D9F-03881CC0B98D}"
dst_ap="36:19:86:e0:2e:0f"; mymac="90:de:80:1c:6a:7a"
data={}; dropped=False; nack_sent=False
def cb(p):
    global dropped,nack_sent
    try:
        if Ether not in p or p[Ether].type != 0x88b5: return
        pl=bytes(p)[14:]
        if len(pl)<16: return
        magic,seq,ln,flags,rsv=struct.unpack("!IIHHI", pl[:16])
        if magic != 0x52544331: return
        payload=pl[16:16+ln]
        if seq==5 and not dropped:
            dropped=True
            print("drop seq5, send NACK",flush=True)
            n=Raw(b"NACK:5")
            sendp(Ether(src=mymac,dst=dst_ap,type=0x88b5)/n,iface=iface,verbose=False)
            nack_sent=True
            return
        data[seq]=payload
        if seq==5 and dropped:
            print("got retransmit seq5",flush=True)
    except Exception as e: pass
sniff(iface=iface, timeout=6, prn=cb, store=False)
print("chunks",len(data),"nack",nack_sent,"max",max(data) if data else -1,flush=True)
if data:
    mx=max(data); out=bytearray(); miss=0
    for i in range(mx+1):
        if i in data: out+=data[i]
        else: miss+=1
    open(r"C:\Temp\recv_nack.h264","wb").write(out)
    print("bytes",len(out),"missing",miss,"sha",hashlib.sha256(out).hexdigest()[:16],flush=True)
