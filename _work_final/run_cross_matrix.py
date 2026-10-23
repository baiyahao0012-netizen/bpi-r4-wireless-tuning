# -*- coding: utf-8 -*-
import subprocess, re, csv, time, statistics

HOST = "root@192.168.240.1"
IPERF = r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8", HOST]

MAC3 = "90:de:80:1c:6a:7a"
MAC6 = "98:6e:e8:28:0c:28"
IP3 = "192.168.240.126"
IP6 = "192.168.240.184"
DUR = 10

def sh(cmd, timeout=30):
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")

def clear_vip():
    sh("nft delete table ip vip 2>/dev/null; true")

def set_vip(ip):
    sh("/root/vip_set.sh %s" % ip)

def airtime(iface, mac):
    p = "/sys/kernel/debug/ieee80211/phy0/netdev:phy0.%s-ap0/stations/%s/airtime" % (iface, mac)
    out = sh("grep '^TX:' %s 2>/dev/null" % p)
    m = re.search(r"TX:\s*(\d+)\s*us", out)
    return int(m.group(1)) / 1e6 if m else 0.0

def parse(out):
    recv = re.findall(r"receiver\s+([0-9.]+)\s+Mbits/sec", out)
    if not recv:
        recv = re.findall(r"([0-9.]+)\s+Mbits/sec\s+receiver", out)
    retr = re.findall(r"Mbits/sec\s+(\d+)\s+sender", out)
    return (float(recv[-1]) if recv else 0.0, int(retr[-1]) if retr else -1)

def run_pair():
    b3 = airtime("1", MAC3); b6 = airtime("0", MAC6)
    p3 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", IP3, "-p", "5201", "-t", str(DUR), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    p6 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", IP6, "-p", "5202", "-t", str(DUR), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    outs = []
    for p in (p3, p6):
        try:
            out, _ = p.communicate(timeout=DUR + 15)
        except subprocess.TimeoutExpired:
            p.kill(); out, _ = p.communicate()
        outs.append(out)
    a3 = airtime("1", MAC3); a6 = airtime("0", MAC6)
    return parse(outs[0]), parse(outs[1]), a3-b3, a6-b6

def main():
    sh("pkill iperf3 2>/dev/null; sleep 1; iperf3 -s -p 5201 -D; iperf3 -s -p 5202 -D; sleep 1; pidof iperf3")
    clear_vip()
    rows = []
    for case, vip in (("baseline", None), ("VIP_5G", IP3)):
        for rnd in range(1, 4):
            if vip: set_vip(vip)
            else: clear_vip()
            time.sleep(1)
            (v3, r3), (v6, r6), a3, a6 = run_pair()
            rows.append([case, rnd, round(v3,1), round(v6,1), round(v3/v6 if v6 else 0,2), r3, r6, round(a3,2), round(a6,2)])
            print("%-10s r%d  5G %6.1f  2.4G %5.1f  ratio %6.2f  retr %d/%d  air %.2f/%.2f" % (case, rnd, v3, v6, (v3/v6 if v6 else 0), r3, r6, a3, a6), flush=True)
    clear_vip()
    out = r"_work_final\vip_cross_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case","round","wlan3_5g_mbps","wlan6_24g_mbps","ratio_5g_24g","retr3","retr6","airtime3_s","airtime6_s"])
        w.writerows(rows)
    print("SAVED", out)
    print("\n=== SUMMARY ===")
    from collections import defaultdict
    g = defaultdict(list)
    for r in rows: g[r[0]].append(r)
    for k, rs in g.items():
        v3 = statistics.mean([r[2] for r in rs]); v6 = statistics.mean([r[3] for r in rs])
        a3 = statistics.mean([r[7] for r in rs]); a6 = statistics.mean([r[8] for r in rs])
        print("%-10s 5G %6.1f  2.4G %5.1f  ratio %6.2f  airtime %.2f/%.2f" % (k, v3, v6, (v3/v6 if v6 else 0), a3, a6))

if __name__ == "__main__":
    main()
