#!/usr/bin/env python3
# quick_clamp_test.py — confirm the clamp printk fires when BA session restarts under traffic
import subprocess, time, os, sys

BOARD = '192.168.1.1'
IPERF = r'D:\Download\iperf3.22_64\iperf3.22\iperf3.exe'
CAP_PATH = '/sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap'

def ssh(cmd, t=20):
    r = subprocess.run(['ssh','-o','StrictHostKeyChecking=no','-o','ConnectTimeout=8',
                        'root@'+BOARD, cmd], capture_output=True, timeout=t)
    return r.returncode, r.stdout.decode('utf-8','replace'), r.stderr.decode('utf-8','replace')

# 1. clear dmesg + reset cap
ssh('dmesg -C; echo 0 > %s' % CAP_PATH)
print('[clear] dmesg cleared, cap=0')

# 2. start downlink iperf3 (board->PC), 25s
logfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_clamp_tmp.txt')
if os.path.exists(logfile): os.remove(logfile)
p = subprocess.Popen([IPERF,'-c',BOARD,'-p','5201','-R','-t','25','-i','1',
                      '--logfile',logfile,'--forceflush'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('[iperf3] started pid=%d (downlink, 25s)' % p.pid)

# 3. wait 6s for BA session established, then write cap=8
time.sleep(6)
rc,out,err = ssh('echo 8 > %s' % CAP_PATH)
print('[write cap=8] rc=%d' % rc)

# 4. wait 8s for BA restart under traffic
time.sleep(8)
rc,out,err = ssh('dmesg | grep -E "aggcap_dbg|agg_win_cap" | tail -60')
print('[dmesg trace lines]')
print(out.strip() if out.strip() else '(none)')

# 5. wait for iperf to finish
p.wait()
print('[iperf3] done')

# 6. show last 6 lines of iperf log
with open(logfile,'r',errors='replace') as f:
    lines=[l for l in f if l.strip()]
print('[iperf3 tail]')
print(''.join(lines[-6:]))
