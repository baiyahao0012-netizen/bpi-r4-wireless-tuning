# -*- coding: utf-8 -*-
import subprocess, re, csv, time, statistics

HOST = "root@192.168.240.1"
IPERF = r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8", HOST]

MAC3 = "90:de:80:1c:6a:7a"
MAC5 = "40:a5:ef:26:e3:47"
IP3 = "192.168.240.126"
IP5 = "192.168.240.232"
DUR = 10

def sh(cmd, timeout=30):
    r = subprocess.run(SSH + [cmd], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")

def clear_vip():
    sh("nft delete table ip vip 2>/dev/null; true")

def set_vip(ip):
    sh("/root/vip_set.sh %s" % ip)

def airtime(mac):
    p = "/sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/%s/airtime" % mac
    out = sh("grep '^TX:' %s 2>/dev/null" % p)
    m = re.search(r"TX:\s*(\d+)\s*us", out)
    return int(m.group(1)) / 1e6 if m else 0.0

def rates():
    out = sh("iw dev phy0.1-ap0 station dump")
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
    return parse(out), out

def run_pair():
    b3 = airtime(MAC3); b5 = airtime(MAC5)
    p3 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", IP3, "-p", "5201", "-t", str(DUR), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    p5 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", IP5, "-p", "5202", "-t", str(DUR), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    outs = []
    for p in (p3, p5):
        try:
            out, _ = p.communicate(timeout=DUR + 15)
        except subprocess.TimeoutExpired:
            p.kill(); out, _ = p.communicate()
        outs.append(out)
    a3 = airtime(MAC3); a5 = airtime(MAC5)
    return parse(outs[0]), parse(outs[1]), a3-b3, a5-b5

def main():
    sh("pkill iperf3 2>/dev/null; sleep 1; iperf3 -s -p 5201 -D; iperf3 -s -p 5202 -D; sleep 1; pidof iperf3")
    clear_vip()
    rows = []
    print("=== solo ===", flush=True)
    for name, ip, port in (("solo_WLAN3", IP3, 5201), ("solo_WLAN5", IP5, 5202)):
        b3 = airtime(MAC3); b5 = airtime(MAC5)
        (v, r), out = run_one(ip, port)
        a3 = airtime(MAC3); a5 = airtime(MAC5)
        vals = (v, 0.0) if name.endswith("WLAN3") else (0.0, v)
        rt = rates()
        rows.append([name, 1, vals[0], vals[1], 0.0, r, -1, round(a3-b3,2), round(a5-b5,2), rt.get(MAC3,"?"), rt.get(MAC5,"?"), ""])
        print(name, "%.1f Mbit/s retr=%d" % (v, r), flush=True)

    for case, vip in (("baseline", None), ("VIP_fast_WLAN3", IP3), ("VIP_slow_WLAN5", IP5)):
        for rnd in range(1, 4):
            if vip: set_vip(vip)
            else: clear_vip()
            time.sleep(1)
            (v3, r3), (v5, r5), a3, a5 = run_pair()
            ratio = v3 / v5 if v5 > 1e-6 else 0.0
            rt = rates()
            rows.append([case, rnd, round(v3,1), round(v5,1), round(ratio,2), r3, r5, round(a3,2), round(a5,2), rt.get(MAC3,"?"), rt.get(MAC5,"?"), vip or ""])
            print("%-18s r%d  WLAN3 %6.1f  WLAN5 %6.1f  ratio %5.2f  retr %d/%d  air %.2f/%.2f" % (case, rnd, v3, v5, ratio, r3, r5, a3, a5), flush=True)
    clear_vip()
    out = r"_work_final\vip_5g_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case","round","wlan3_mbps","wlan5_mbps","ratio_3_5","retr3","retr5","airtime3_s","airtime5_s","mcs3","mcs5","vip_ip"])
        w.writerows(rows)
    print("SAVED", out)
    print("\n=== SUMMARY ===")
    from collections import defaultdict
    g = defaultdict(list)
    for row in rows:
        if row[0].startswith("solo"): continue
        g[row[0]].append(row)
    for k, rs in g.items():
        v3 = statistics.mean([r[2] for r in rs]); v5 = statistics.mean([r[3] for r in rs])
        a3 = statistics.mean([r[7] for r in rs]); a5 = statistics.mean([r[8] for r in rs])
        print("%-18s WLAN3 %6.1f  WLAN5 %6.1f  ratio %5.2f  airtime %5.2f/%5.2f" % (k, v3, v5, (v3/v5 if v5 else 0), a3, a5))

if __name__ == "__main__":
    main()
