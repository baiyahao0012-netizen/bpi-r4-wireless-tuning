# -*- coding: utf-8 -*-
import subprocess, re, csv, time, statistics, os

HOST = "root@192.168.240.1"
IPERF = r"C:\Users\15732\Desktop\iperf3\iperf-3.1.3-win64\iperf3.exe"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8", HOST]

MAC3 = "90:de:80:1c:6a:7a"  # WLAN3 MediaTek 5G
MAC5 = "40:a5:ef:26:e3:47"  # WLAN5 Realtek 8812BU 5G
MAC6 = "98:6e:e8:28:0c:28"  # WLAN6 Ugreen 2.4G
MAC7 = "6c:1f:f7:e1:86:14"  # WLAN7 Ugreen 2.4G

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

def run_iperf(ip, port, dur):
    cmd = [IPERF, "-c", "192.168.240.1", "-B", ip, "-p", str(port), "-t", str(dur), "-R", "-i", "1"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        out, _ = p.communicate(timeout=dur + 15)
    except subprocess.TimeoutExpired:
        p.kill(); out, _ = p.communicate()
    m = re.findall(r"receiver\s+([0-9.]+)\s+Mbits/sec", out)
    if not m:
        m2 = re.findall(r"([0-9.]+)\s+Mbits/sec\s+receiver", out)
        m = m2
    return float(m[-1]) if m else 0.0

def run_pair(vip, normal, dur=8):
    bv = airtime(vip["iface"], vip["mac"]); bn = airtime(normal["iface"], normal["mac"])
    p1 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", vip["ip"], "-p", str(vip["port"]), "-t", str(dur), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    p2 = subprocess.Popen([IPERF, "-c", "192.168.240.1", "-B", normal["ip"], "-p", str(normal["port"]), "-t", str(dur), "-R", "-i", "1"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    outs = []
    for p in (p1, p2):
        try:
            out, _ = p.communicate(timeout=dur + 15)
        except subprocess.TimeoutExpired:
            p.kill(); out, _ = p.communicate()
        outs.append(out)
    def parse(out):
        m = re.findall(r"receiver\s+([0-9.]+)\s+Mbits/sec", out)
        if not m:
            m = re.findall(r"([0-9.]+)\s+Mbits/sec\s+receiver", out)
        return float(m[-1]) if m else 0.0
    av = airtime(vip["iface"], vip["mac"]); an = airtime(normal["iface"], normal["mac"])
    return parse(outs[0]), parse(outs[1]), av - bv, an - bn

def main():
    sh("pkill iperf3 2>/dev/null; sleep 1; iperf3 -s -p 5201 -D; iperf3 -s -p 5202 -D; sleep 1; pidof iperf3")
    clear_vip()
    cases = [
        ("5G_VIP_fast", {"iface":"1","ip":"192.168.240.126","mac":MAC3,"port":5202},
                        {"iface":"1","ip":"192.168.240.232","mac":MAC5,"port":5201}),
        ("5G_VIP_slow", {"iface":"1","ip":"192.168.240.232","mac":MAC5,"port":5201},
                        {"iface":"1","ip":"192.168.240.126","mac":MAC3,"port":5202}),
        ("2.4G_VIP_6", {"iface":"0","ip":"192.168.240.184","mac":MAC6,"port":5201},
                       {"iface":"0","ip":"192.168.240.219","mac":MAC7,"port":5202}),
        ("2.4G_VIP_7", {"iface":"0","ip":"192.168.240.219","mac":MAC7,"port":5202},
                       {"iface":"0","ip":"192.168.240.184","mac":MAC6,"port":5201}),
        ("cross_band_VIP_5G", {"iface":"1","ip":"192.168.240.126","mac":MAC3,"port":5202},
                              {"iface":"0","ip":"192.168.240.184","mac":MAC6,"port":5201}),
    ]
    rows = []
    for name, vip, normal in cases:
        for mode in ("baseline", "vip"):
            for rnd in range(1, 4):
                if mode == "vip":
                    set_vip(vip["ip"])
                else:
                    clear_vip()
                time.sleep(1)
                v, n, av, an = run_pair(vip, normal, 8)
                ratio = v / n if n > 1e-6 else 0.0
                aratio = av / an if an > 1e-6 else 0.0
                rows.append([name, mode, rnd, round(v,1), round(n,1), round(ratio,2), round(av,2), round(an,2), round(aratio,2)])
                print("%-20s %-8s r%d VIP %6.1f  normal %6.1f  ratio %5.2f  airtime %.2f/%.2f" % (name, mode, rnd, v, n, ratio, av, an), flush=True)
    clear_vip()
    out = r"_work_final\vip_matrix_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case","mode","round","vip_mbps","normal_mbps","throughput_ratio","vip_airtime_s","normal_airtime_s","airtime_ratio"])
        w.writerows(rows)
    print("SAVED", out)
    # summary
    from collections import defaultdict
    g = defaultdict(list)
    for row in rows:
        g[(row[0], row[1])].append(row)
    print("\n=== SUMMARY ===")
    for k in g:
        rs = g[k]
        v = statistics.mean([r[3] for r in rs]); n = statistics.mean([r[4] for r in rs])
        av = statistics.mean([r[6] for r in rs]); an = statistics.mean([r[7] for r in rs])
        print("%-20s %-8s VIP %6.1f  normal %6.1f  thr-ratio %5.2f  airtime %5.2f/%5.2f" % (k[0], k[1], v, n, (v/n if n else 0), av, an))

if __name__ == "__main__":
    main()
