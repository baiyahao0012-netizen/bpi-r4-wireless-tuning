# -*- coding: utf-8 -*-
import subprocess, time, csv, statistics, re
HOST="root@192.168.240.1"
IPERF=r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
CURL=r"C:\Windows\System32\curl.exe"
SSH=["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=no","-o","ConnectTimeout=8",HOST]
def sh(c):
    r=subprocess.run(SSH+[c],capture_output=True,text=True,timeout=30)
    return (r.stdout or "")+(r.stderr or "")
def accel(on): sh("/root/oaf_accel.sh install 1900 ef" if on else "/root/oaf_accel.sh remove")
def probe():
    r=subprocess.run([CURL,"--interface","192.168.240.126","-k","-s","-o","NUL","-w","%{time_starttransfer}", "https://www.doubao.com/"],capture_output=True,text=True,timeout=30)
    try: return float(r.stdout.strip())
    except: return 0.0
def main():
    rows=[]
    for rnd in range(1,4):
        for mode,on in (("A",False),("B",True)):
            accel(on); time.sleep(1)
            sh("pkill iperf3 2>/dev/null; sleep 1; iperf3 -s -p 5201 -D; sleep 1")
            load=subprocess.Popen([IPERF,"-c","192.168.240.1","-B","192.168.240.126","-p","5201","-t","15","-R","-i","5"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            time.sleep(2)
            vals=[probe() for _ in range(8)]
            try: out,_=load.communicate(timeout=25)
            except subprocess.TimeoutExpired: load.kill(); out,_=load.communicate()
            m=re.findall(r"receiver\s+([0-9.]+)\s+Mbits/sec",out)
            bw=float(m[-1]) if m else 0.0
            if not m: print("NOLOAD",out[-400:].replace("\n"," | "),flush=True)
            rows.append([rnd,mode,round(bw,1)]+[round(v,4) for v in vals])
            print("r%d %s load=%.1f vals=%s"%(rnd,mode,bw,",".join("%.3f"%v for v in vals)),flush=True)
    with open(r"_work_final\oaf_accel\pc_ab_rounds.csv","w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["round","mode","load_mbps"]+["ttfb_%d"%i for i in range(1,9)]); w.writerows(rows)
    print("SAVED")
    for mode in ("A","B"):
        g=[x for row in rows if row[1]==mode for x in row[3:] if x>0]
        print(mode,"n",len(g),"mean",round(statistics.mean(g),3),"p50",round(statistics.median(g),3),"p95",round(sorted(g)[int(len(g)*0.95)-1],3))
if __name__=="__main__": main()
