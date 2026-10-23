# -*- coding: utf-8 -*-
import subprocess, re, csv, time, statistics

HOST = "root@192.168.240.1"
IPERF = r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8", HOST]

MAC6 = "98:6e:e8:28:0c:28"
MAC7 = "6c:1f:f7:e1:86:14"
IP6 = "192.168.240.184"
IP7 = "192.168.240.219"
DUR = 10

def sh(cmd, timeout=30):
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")

def clear_vip():
    sh("nft delete table ip vip 2>/dev/null; true")

def set_vip(ip):
    sh("/root/vip_set.sh %s" % ip)

def airtime(mac):
    p = "/sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-ap0/stations/%s/airtime" % mac
    out = sh("grep '^TX:' %s 2>/dev/null" % p)
    m = re.search(r"TX:\s*(\d+)\s*us", out)
    return int(m.group(1)) / 1e6 if m else 0.0

def rates():
    out = sh("iw dev phy0.0-ap0 station dump")
    res = {}
    blocks = re.split(r"Station\s+([0-9a-f:]{17})", out)
    for i in range(1, len(blocks), 2):
        mac = blocks[i]; body = blocks[i+1]
        m = re.search(r"tx bitrate:\s*([0-9.]+) MBit/s\s*([^\n]*)", body)
        res[mac] = ("%.1f %s" % (float(m.group(1)), m.group(2).strip())) if m else "?"
    return res

def parse(out):
    recv = re.findall(r"receiver\s+([0-9.]+)\s+Mbits/sec", out)
    if not recv:
        recv = re.findall(r"([0-9.]+)\s+Mbits/sec\s+receiver", out)
    retr = re.findall(r"Mbits/sec\s+(\d+)\s+sender", out)
    return (float(recv[-1]) if recv else 0.0, int(retr[-1]) if retr else -1)

def run_one(ip, port):
    p = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", ip, "-p", str(port), "-t", str(DUR), "-R", "-i", "1"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        out, _ = p.communicate(timeout=DUR + 15)
    except subprocess.TimeoutExpired:
        p.kill(); out, _ = p.communicate()
    return parse(out)

def run_pair():
    b6 = airtime(MAC6); b7 = airtime(MAC7)
    p6 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", IP6, "-p", "5201", "-t", str(DUR), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    p7 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", IP7, "-p", "5202", "-t", str(DUR), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    outs = []
    for p in (p6, p7):
        try:
            out, _ = p.communicate(timeout=DUR + 15)
        except subprocess.TimeoutExpired:
            p.kill(); out, _ = p.communicate()
        outs.append(out)
    a6 = airtime(MAC6); a7 = airtime(MAC7)
    return parse(outs[0]), parse(outs[1]), a6-b6, a7-b7

def main():
    sh("pkill iperf3 2>/dev/null; sleep 1; iperf3 -s -p 5201 -D; iperf3 -s -p 5202 -D; sleep 1; pidof iperf3")
    clear_vip()
    rows = []
    print("=== solo ===", flush=True)
    for name, ip, port in (("solo_WLAN6", IP6, 5201), ("solo_WLAN7", IP7, 5202)):
        b6 = airtime(MAC6); b7 = airtime(MAC7)
        v, r = run_one(ip, port)
        a6 = airtime(MAC6); a7 = airtime(MAC7)
        vals = (v, 0.0) if name.endswith("WLAN6") else (0.0, v)
        rt = rates()
        rows.append([name, 1, vals[0], vals[1], 0.0, r, -1, round(a6-b6,2), round(a7-b7,2), rt.get(MAC6,"?"), rt.get(MAC7,"?"), ""])
        print(name, "%.1f Mbit/s retr=%d" % (v, r), flush=True)

    for case, vip in (("baseline", None), ("VIP_WLAN6", IP6), ("VIP_WLAN7", IP7)):
        for rnd in range(1, 4):
            if vip: set_vip(vip)
            else: clear_vip()
            time.sleep(1)
            (v6, r6), (v7, r7), a6, a7 = run_pair()
            ratio = v6 / v7 if v7 > 1e-6 else 0.0
            rt = rates()
            rows.append([case, rnd, round(v6,1), round(v7,1), round(ratio,2), r6, r7, round(a6,2), round(a7,2), rt.get(MAC6,"?"), rt.get(MAC7,"?"), vip or ""])
            print("%-14s r%d  WLAN6 %5.1f  WLAN7 %5.1f  ratio %5.2f  retr %d/%d  air %.2f/%.2f" % (case, rnd, v6, v7, ratio, r6, r7, a6, a7), flush=True)
    clear_vip()
    out = r"_work_final\vip_24g_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case","round","wlan6_mbps","wlan7_mbps","ratio_6_7","retr6","retr7","airtime6_s","airtime7_s","mcs6","mcs7","vip_ip"])
        w.writerows(rows)
    print("SAVED", out)
    print("\n=== SUMMARY ===")
    from collections import defaultdict
    g = defaultdict(list)
    for row in rows:
        if row[0].startswith("solo"): continue
        g[row[0]].append(row)
    for k, rs in g.items():
        v6 = statistics.mean([r[2] for r in rs]); v7 = statistics.mean([r[3] for r in rs])
        a6 = statistics.mean([r[7] for r in rs]); a7 = statistics.mean([r[8] for r in rs])
        print("%-14s WLAN6 %5.1f  WLAN7 %5.1f  ratio %5.2f  airtime %5.2f/%5.2f" % (k, v6, v7, (v6/v7 if v7 else 0), a6, a7))

if __name__ == "__main__":
    main()
