"""Local receiver and bounded cross-over tests; no phone traffic."""
import argparse
import csv
import json
import pathlib
import re
import socket
import subprocess
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent
PLINK = r"D:\Bai_Yahao\Software\PuTTY\plink.exe"
KEY = "SHA256:5vJReXAV29P56hpD1C7QxmkSI2v64oYDdyXFCSypH8E"
BASE = [PLINK, "-ssh", "-batch", "-hostkey", KEY, "root@192.168.240.1"]
stop = threading.Event()
totals = {}
errors = []


def remote(cmd, timeout=15):
    return subprocess.run(BASE + [cmd], capture_output=True, timeout=timeout)


def receive(ip, port, echo):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
            # Windows IP_UNICAST_IF takes the interface index in network order.
            index = 21 if ip.endswith(".147") else 24
            s.setsockopt(socket.IPPROTO_IP, 31, socket.htonl(index))
            s.bind((ip, port))
            s.settimeout(0.2)
            while not stop.is_set():
                try:
                    data, addr = s.recvfrom(65535)
                    totals[port] = totals.get(port, 0) + len(data)
                    if echo:
                        s.sendto(data, ("192.168.240.1", 6203))
                except socket.timeout:
                    pass
    except Exception as exc:
        errors.append(str(exc))


def quantile(xs, q):
    xs = sorted(xs)
    return xs[round((len(xs) - 1) * q)] if xs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--seconds", type=int, default=20)
    ap.add_argument("--rate", type=float, default=100)
    args = ap.parse_args()
    out = ROOT / ("pc_edca_" + time.strftime("%Y%m%d_%H%M%S"))
    out.mkdir()
    for ip, port, echo in [
        ("192.168.240.147", 6201, True),
        ("192.168.240.147", 6202, False),
        ("192.168.240.126", 6204, False),
    ]:
        threading.Thread(target=receive, args=(ip, port, echo), daemon=True).start()
    time.sleep(0.5)
    snapshot = "date; iw dev phy0.1-ap0 station dump; iw dev phy0.1-ap0 survey dump; nft list ruleset; tc qdisc show dev phy0.1-ap0"
    results = []
    # A is an explicit reference, not a claimed firmware factory default.
    profiles = [
        ("idle", None, 0),
        ("A1", "2 3 7 47", args.rate),
        ("B1", "1 1 3 94", args.rate),
        ("B2", "1 1 3 94", args.rate),
        ("A2", "2 3 7 47", args.rate),
    ]
    if args.pilot:
        profiles = [("pilot", None, 0)]
    try:
        for name, vo, rate in profiles:
            if vo:
                r = remote("/root/edca_set phy0.1-ap0 3 " + vo)
                (out / (name + "_edca.txt")).write_bytes(r.stdout + r.stderr)
                if r.returncode:
                    raise RuntimeError("EDCA command failed")
            (out / (name + "_before.txt")).write_bytes(remote(snapshot).stdout)
            before = dict(totals)
            start = time.monotonic()
            cmd = ("/tmp/edca_probe phy0.1-ap0 192.168.240.147 "
                   "c0:35:32:19:cc:fb 192.168.240.126 90:de:80:1c:6a:7a "
                   f"{args.seconds} {rate} 262")
            r = remote(cmd, args.seconds + 15)
            (out / (name + "_rtt.csv")).write_bytes(r.stdout)
            (out / (name + "_sender.txt")).write_bytes(r.stderr)
            elapsed = time.monotonic() - start
            received = {str(k): v - before.get(k, 0) for k, v in totals.items()}
            if r.returncode:
                raise RuntimeError(r.stderr.decode(errors="replace"))
            rows = list(csv.DictReader(r.stdout.decode().splitlines()))
            # Exclude the first three seconds of each measurement.
            steady = [float(x["rtt_ms"]) for x in rows
                      if 3 <= float(x["elapsed_s"]) < args.seconds]
            match = re.search(rb"flow=0 priority=\d+ sent=(\d+)", r.stderr)
            sent = int(match[1]) if match else None
            summary = {
                "condition": name, "vo_aifs_cwmin_cwmax_txop": vo,
                "background_target_mbps_each": rate,
                "seconds": args.seconds, "wall_seconds": elapsed,
                "probe_sent": sent, "echo_received": len(rows),
                "echo_missing_pct": 100 * (1 - len(rows) / sent) if sent else None,
                "steady_rtt_n": len(steady),
                "p50_ms": quantile(steady, .5), "p95_ms": quantile(steady, .95),
                "p99_ms": quantile(steady, .99), "max_ms": max(steady) if steady else None,
                "received_bytes": received, "receiver_errors": errors[:],
            }
            results.append(summary)
            (out / (name + "_after.txt")).write_bytes(remote(snapshot).stdout)
            (out / "results.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(summary), flush=True)
            if not rows:
                raise RuntimeError("No echoed probe packets; do not continue")
            time.sleep(2)
    finally:
        # Restore the exact last-commanded VO profile from before this test.
        restore = remote("/root/edca_set phy0.1-ap0 3 3 7 15 0")
        (out / "restore.txt").write_bytes(restore.stdout + restore.stderr)
        stop.set()
        print("RESULT_DIR=" + str(out), flush=True)


if __name__ == "__main__":
    main()
