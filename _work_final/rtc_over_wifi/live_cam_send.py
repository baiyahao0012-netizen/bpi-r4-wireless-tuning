import subprocess, time, struct, sys
from scapy.all import Ether, Raw, sendp
iface=r"\Device\NPF_{C33D086D-AA6B-4D75-8D9F-03881CC0B98D}"
src="90:de:80:1c:6a:7a"; dst="c0:35:32:19:cc:fb"
ff=r"D:\Bai_Yahao\Software\Python\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
cmd=[ff,"-hide_banner","-loglevel","error","-f","dshow","-rtbufsize","64M","-i","video=Integrated Camera","-t","6","-c:v","libx264","-preset","ultrafast","-tune","zerolatency","-x264-params","aud=1:threads=1","-pix_fmt","yuv420p","-f","h264","pipe:1"]
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
buf=b""; seq=0; frames=0; t0=time.time()
def send_frame(frame):
    global seq,frames
    ts=int((time.time()-t0)*1000)&0xffffffff
    off=0
    while off<len(frame):
        n=min(1200,len(frame)-off)
        hdr=struct.pack("!IIHHI",0x52544331,seq,n,0,ts)
        pkt=Ether(src=src,dst=dst,type=0x88b5)/Raw(hdr+frame[off:off+n])
        sendp(pkt,iface=iface,verbose=False)
        seq+=1; off+=n
    frames+=1
while True:
    chunk=p.stdout.read(4096)
    if not chunk: break
    buf+=chunk
    while True:
        # find AUD start (00 00 01 09 or 00 00 00 01 09)
        best=-1; blen=0
        for pat,ln in ((b"\x00\x00\x01\x09",4),(b"\x00\x00\x00\x01\x09",5)):
            i=buf.find(pat,1)
            if i>=0 and (best<0 or i<best): best=i; blen=ln
        if best<0: break
        frame=buf[:best]; buf=buf[best:]
        if len(frame)>0: send_frame(frame)
if len(buf)>0: send_frame(buf)
print("sent frames",frames,"chunks",seq,"sec",round(time.time()-t0,2))
