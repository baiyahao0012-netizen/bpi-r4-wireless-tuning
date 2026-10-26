# -*- coding: utf-8 -*-
import subprocess, time, re, csv, os, statistics
HOST="root@192.168.240.1"; MAC="90:de:80:1c:6a:7a"; IP="192.168.240.126"
CURL=r"C:\Windows\System32\curl.exe"
IPERF=r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
FF=subprocess.check_output(["python","-c","import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],text=True).strip()
SSH=["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=no","-o","ConnectTimeout=8",HOST]
def sh(c): return subprocess.run(SSH+[c],capture_output=True,text=True,timeout=30)
def wifi(ssid):
    subprocess.run(["netsh","wlan","connect",f"name={ssid}","interface=WLAN 3"],capture_output=True,text=True,timeout=20)
    time.sleep(8)
    subprocess.run(["ipconfig","/renew","WLAN 3"],capture_output=True,text=True,timeout=20)
    time.sleep(2)
def frames(path):
    if not os.path.exists(path): return 0
    r=subprocess.run([FF,"-y","-i",path,"-f","null","-"],capture_output=True,text=True,timeout=30)
    m=re.findall(r"frame=\s*(\d+)",r.stderr)
    return int(m[-1]) if m else 0
def recv(script,outfile):
    p=subprocess.Popen(["python",script],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    time.sleep(2.0)
    return p
def finish(p,outfile):
    out,_=p.communicate(timeout=25)
    chunks=re.search(r"chunks\s+(\d+)",out); miss=re.search(r"missing\s+(\d+)",out); byt=re.search(r"bytes\s+(\d+)",out); sha=re.search(r"sha\s+([0-9a-f]+)",out); span=re.search(r"span\s+([0-9.]+)",out)
    return dict(chunks=int(chunks.group(1)) if chunks else 0, missing=int(miss.group(1)) if miss else 0, bytes=int(byt.group(1)) if byt else 0, sha=sha.group(1) if sha else "", span=float(span.group(1)) if span else 0.0, raw=out.strip(), frames=frames(outfile))
def run_udp():
    p=recv(r"_work_recover\udp_video_recv.py",r"C:\Temp\recv_udp.h264")
    time.sleep(0.5)
    sh("/root/udp_video_send 192.168.240.126 5000 /root/cam6.h264 30")
    r=finish(p,r"C:\Temp\recv_udp.h264"); r["method"]="UDP/IP"; return r
def run_l2(iface):
    p=recv(r"_work_recover\l2video_recv_rt.py",r"C:\Temp\recv_rt.h264")
    time.sleep(0.5)
    sh(f"/root/l2video_send_rt {iface} {MAC} /root/cam6.h264 30")
    r=finish(p,r"C:\Temp\recv_rt.h264"); r["method"]="RT-L2"; return r
def scenario(name,ssid,iface,load=False):
    wifi(ssid)
    loadp=None
    if load:
        sh("pkill iperf3 2>/dev/null; sleep 1; iperf3 -s -p 5201 -D; sleep 1")
        loadp=subprocess.Popen([IPERF,"-c","192.168.240.1","-B",IP,"-p","5201","-t","60","-R","-i","10"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        time.sleep(1)
    rows=[]
    for i in range(1,4):
        r=run_udp(); r.update(scenario=name,run=i); rows.append(r); print(name,i,"UDP",r["chunks"],r["missing"],r["bytes"],r["frames"],flush=True)
        r=run_l2(iface); r.update(scenario=name,run=i); rows.append(r); print(name,i,"L2",r["chunks"],r["missing"],r["bytes"],r["frames"],flush=True)
    if loadp: loadp.terminate()
    sh("pkill iperf3 2>/dev/null; true")
    return rows
def main():
    rows=[]
    rows+=scenario("5G_IDLE","BPI-R4-5G","phy0.1-ap0",False)
    rows+=scenario("5G_LOAD","BPI-R4-5G","phy0.1-ap0",True)
    rows+=scenario("2G4","BPI-R4","phy0.0-ap0",False)
    with open(r"_work_final\rtc_over_wifi\matrix_raw.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["scenario","run","method","chunks","missing","bytes","span","frames","sha","raw"]); w.writeheader(); w.writerows(rows)
    print("SAVED")
    for sc in ("5G_IDLE","5G_LOAD","2G4"):
        for m in ("UDP/IP","RT-L2"):
            g=[r for r in rows if r["scenario"]==sc and r["method"]==m]
            print(sc,m,"n",len(g),"chunks",[x["chunks"] for x in g],"missing",[x["missing"] for x in g],"frames",[x["frames"] for x in g])
if __name__=="__main__": main()
