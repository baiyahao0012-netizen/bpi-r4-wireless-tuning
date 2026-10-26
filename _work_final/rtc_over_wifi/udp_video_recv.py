import socket, struct, time, hashlib
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("0.0.0.0",5000)); s.settimeout(5)
data={}; ts={}; t0=time.time(); first=None; last=None
while time.time()-t0<8:
    try: pkt,addr=s.recvfrom(2048)
    except socket.timeout: break
    if len(pkt)<16: continue
    magic,seq,ln,flags,rv=struct.unpack("!IIHHI",pkt[:16])
    if magic!=0x52544331: continue
    if first is None: first=time.time()
    last=time.time(); data[seq]=pkt[16:16+ln]; ts[seq]=rv
print("chunks",len(data),"max",max(data) if data else -1,"span",round(last-first,3) if first else 0)
if data:
    mx=max(data); out=bytearray(); miss=0
    for i in range(mx+1):
        if i in data: out+=data[i]
        else: miss+=1
    open(r"C:\Temp\recv_udp.h264","wb").write(out)
    print("missing",miss,"bytes",len(out),"sha",hashlib.sha256(out).hexdigest()[:16])
