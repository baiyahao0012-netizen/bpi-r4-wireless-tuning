# -*- coding: utf-8 -*-
import subprocess, re, csv, time, statistics
HOST="root@192.168.240.1"
IPERF=r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
SSH=["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=no","-o","ConnectTimeout=8",HOST]
MAC3="90:de:80:1c:6a:7a"; MAC5="40:a5:ef:26:e3:47"
IP3="192.168.240.126"; IP5="192.168.240.232"
def sh(c): 
    r=subprocess.run(SSH+[c],capture_output=True,text=True,timeout=30)
    return (r.stdout or "")+(r.stderr or "")
def set_limit(mb):
    sh("nft delete table ip vipq 2>/dev/null")
    sh("nft add table ip vipq")
    sh("nft add chain ip vipq out '{ type filter hook output priority 0; }'")
    sh("nft add rule ip vipq out ip daddr %s limit rate %d mbytes/second accept" % (IP5, mb))
    sh("nft add rule ip vipq out ip daddr %s drop" % IP5)
def air(mac):
    p="/sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/%s/airtime"%mac
    m=re.search(r"TX:\s*(\d+)\s*us",sh("grep '^TX:' "+p))
    return int(m.group(1))/1e6 if m else 0.0
def parse(o):
    r=re.findall(r"receiver\s+([0-9.]+)\s+Mbits/sec",o) or re.findall(r"([0-9.]+)\s+Mbits/sec\s+receiver",o)
    t=re.findall(r"Mbits/sec\s+(\d+)\s+sender",o)
    return (float(r[-1]) if r else 0.0, int(t[-1]) if t else -1)
def run():
    b3=air(MAC3); b5=air(MAC5)
    p3=subprocess.Popen([IPERF,"-c","192.168.240.1","-B",IP3,"-p","5201","-t","10","-R","-i","1"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    p5=subprocess.Popen([IPERF,"-c","192.168.240.1","-B",IP5,"-p","5202","-t","10","-R","-i","1"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    outs=[]
    for p in (p3,p5):
        try: o,_=p.communicate(timeout=25)
        except subprocess.TimeoutExpired: p.kill(); o,_=p.communicate()
        outs.append(o)
    return parse(outs[0]),parse(outs[1]),air(MAC3)-b3,air(MAC5)-b5
rows=[]
for name,mb in (("4to1",9),):
    for rnd in range(1,4):
        set_limit(mb); time.sleep(1)
        (v3,r3),(v5,r5),a3,a5=run()
        rows.append([name,mb,rnd,round(v3,1),round(v5,1),round(v3/v5 if v5 else 0,2),r3,r5,round(a3,2),round(a5,2)])
        print("%-5s mb=%2d r%d  VIP %6.1f  normal %5.1f  ratio %5.2f  retr %d/%d"%(name,mb,rnd,v3,v5,(v3/v5 if v5 else 0),r3,r5),flush=True)
sh("nft delete table ip vipq 2>/dev/null")
with open(r"_work_final\aplus_policer_4to1_9.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["case","normal_limit_mbytes_s","round","vip_mbps","normal_mbps","ratio","retr_vip","retr_normal","vip_airtime_s","normal_airtime_s"]); w.writerows(rows)
print("SAVED")
from collections import defaultdict
g=defaultdict(list)
for r in rows: g[r[0]].append(r)
for k,rs in g.items():
    print(k,"VIP",round(statistics.mean([r[3] for r in rs]),1),"normal",round(statistics.mean([r[4] for r in rs]),1),"ratio",round(statistics.mean([r[5] for r in rs]),2))
