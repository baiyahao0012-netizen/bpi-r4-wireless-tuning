#!/bin/bash
# Runs on Pi. AP-side sender + AP TC classification + Pi client TTFT.
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
AP_MAC=36:19:86:e0:2e:0f
PI_MAC=90:de:80:1c:6a:7a

echo "=== setup AP htb + filter ==="
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null
tc qdisc add dev phy0.1-ap0 root handle 1: htb default 20
tc class add dev phy0.1-ap0 parent 1: classid 1:10 htb rate 200mbit ceil 200mbit prio 0 2>/dev/null
tc class add dev phy0.1-ap0 parent 1: classid 1:20 htb rate 20mbit ceil 20mbit prio 1 2>/dev/null
tc filter add dev phy0.1-ap0 parent 1: protocol all basic match "meta(priority eq 0)" flowid 1:10 2>/dev/null
echo htb_ok'

echo "=== start AP sender (bulk 40M, 12s) ==="
$A "cd /tmp && (./l2_ai_ap_tx phy0.1-ap0 $PI_MAC 1200 40 12 >/tmp/ap_tx.log 2>&1 &)"
sleep 1
echo "=== Pi client 8s ==="
echo 12345678 | sudo -S python3 /tmp/l2_ai_client.py --dst-mac $AP_MAC --seconds 8 --msg-base 3000000 --out /tmp/v2_ap.json 2>/dev/null >/dev/null
cat /tmp/v2_ap.json
sleep 5
echo "=== AP sender log ==="
$A 'cat /tmp/ap_tx.log | tail -n 2'
echo "=== AP classes ==="
$A 'tc -s class show dev phy0.1-ap0 | grep -E "class htb|Sent"'
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null; echo cleaned'
