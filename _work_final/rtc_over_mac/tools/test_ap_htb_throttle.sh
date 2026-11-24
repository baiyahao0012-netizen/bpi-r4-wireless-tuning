#!/bin/bash
# Runs on Pi. HTB on AP egress: bulk class 1:20 = 20Mbit, AI class 1:10 = 200Mbit prio 0.
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
pkill -f "iperf3 -s" 2>/dev/null; sleep 1
iperf3 -s -B 192.168.240.126 -p 5201 -D
sleep 1
echo "=== setup HTB ==="
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null
tc qdisc add dev phy0.1-ap0 root handle 1: htb default 20
tc class add dev phy0.1-ap0 parent 1: classid 1:10 htb rate 200mbit ceil 200mbit prio 0 2>/dev/null
tc class add dev phy0.1-ap0 parent 1: classid 1:20 htb rate 20mbit ceil 20mbit prio 1 2>/dev/null
tc filter add dev phy0.1-ap0 parent 1: protocol all u32 match u16 0x88b6 0xffff at 12 flowid 1:10 2>/dev/null
echo setup_ok'
echo "=== UDP 40M AP->Pi 10s (should be throttled to ~20M) ==="
$A 'iperf3 -c 192.168.240.126 -u -b 40M -t 10 -p 5201 2>&1 | tail -n 3'
echo "=== AP classes ==="
$A 'tc -s class show dev phy0.1-ap0 | grep -E "class htb|Sent|dropped"' 
pkill -f "iperf3 -s" 2>/dev/null
echo TC_BULK_DONE
