#!/bin/bash
# Print one JSON line of link covariates for the run record.
# Called on the Pi (it holds the AP ssh key).
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
ST=$($A 'iw dev phy0.1-ap0 station dump 2>/dev/null | sed -n "/90:de:80:1c:6a:7a/,/^Station/p" | grep -E "tx bitrate|rx bitrate|signal:|tx retries|tx failed|tx packets"')
CH=$($A 'iwinfo phy0.1-ap0 info 2>/dev/null | grep -E "Channel|Tx-Power|Signal"')
python3 - "$ST" "$CH" <<'PY'
import json, re, sys, time
st, ch = sys.argv[1], sys.argv[2]
def num(pat, s, cast=float, default=None):
    m = re.search(pat, s)
    return cast(m.group(1)) if m else default
out = {
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "tx_bitrate_mbps": num(r"tx bitrate:\s*([0-9.]+)", st),
    "rx_bitrate_mbps": num(r"rx bitrate:\s*([0-9.]+)", st),
    "signal_dbm": num(r"signal:\s*(-?[0-9.]+)", st),
    "tx_retries": num(r"tx retries:\s*(\d+)", st, int),
    "tx_failed": num(r"tx failed:\s*(\d+)", st, int),
    "tx_packets": num(r"tx packets:\s*(\d+)", st, int),
    "channel": (re.search(r"Channel:\s*(\d+)", ch).group(1) if re.search(r"Channel:\s*(\d+)", ch) else None),
    "txpower_dbm": num(r"Tx-Power:\s*(-?[0-9.]+)", ch),
}
print(json.dumps(out, ensure_ascii=False))
PY
