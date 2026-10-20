#!/usr/bin/env python3
# sweep_test.py — sweep agg_win_cap during downlink iperf3 to see throughput sensitivity
import subprocess, time, os

BOARD='192.168.1.1'
IPERF=r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
CAP='/sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap'
HERE=os.path.dirname(os.path.abspath(__file__))

def ssh(cmd,t=20):
    r=subprocess.run(['ssh','-o','StrictHostKeyChecking=no','-o','ConnectTimeout=8','root@'+BOARD,cmd],
                     capture_output=True,timeout=t)
    return r.returncode,r.stdout.decode('utf-8','replace'),r.stderr.decode('utf-8','replace')

ssh('dmesg -C; echo 0 > %s' % CAP)
print('[clear] dmesg cleared, cap=0')

log=os.path.join(HERE,'_sweep.txt')
if os.path.exists(log): os.remove(log)
p=subprocess.Popen([IPERF,'-c',BOARD,'-p','5201','-R','-t','50','-i','1','--logfile',log,'--forceflush'],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('[iperf3] started pid=%d (50s)'%p.pid)

# schedule writes: (t, cap)
plan=[(5,8),(15,4),(25,2),(35,0)]
t0=time.perf_counter()
for (tt,cap) in plan:
    while time.perf_counter()-t0 < tt: time.sleep(0.02)
    rc,o,e=ssh('echo %d > %s'%(cap,CAP))
    print('[t=%.1f] write cap=%d rc=%d'%(time.perf_counter()-t0,cap,rc))
p.wait()

with open(log,errors='replace') as f: lines=[l.rstrip() for l in f if l.strip()]
print('\n=== per-second throughput ===')
for l in lines:
    if 'sec' in l or 'Bitrate' in l or 'sender' in l or 'receiver' in l:
        print(l)
