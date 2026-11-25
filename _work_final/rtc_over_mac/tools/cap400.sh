#!/bin/bash
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
pkill -x iperf3 2>/dev/null; sleep 1
iperf3 -s -B 192.168.240.126 -p 5208 -D
sleep 1
echo "=== UDP 400M AP->Pi ==="
$A 'iperf3 -c 192.168.240.126 -u -b 400M -t 10 -p 5208 2>&1 | tail -n 3'
echo "=== AP STA 计数 ==="
$A 'iw dev phy0.1-ap0 station dump | sed -n "/90:de:80:1c:6a:7a/,/^Station/p" | grep -E "tx packets|tx retries|tx failed|signal:"'
pkill -x iperf3 2>/dev/null
echo CAP400_DONE
