#!/bin/bash
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
$A 'tc qdisc del dev phy0.1-ap0 root 2>/dev/null
tc qdisc add dev phy0.1-ap0 root handle 1: htb default 20
tc class add dev phy0.1-ap0 parent 1: classid 1:10 htb rate 200mbit ceil 200mbit prio 0 2>/dev/null
tc class add dev phy0.1-ap0 parent 1: classid 1:20 htb rate 20mbit ceil 20mbit prio 1 2>/dev/null
tc filter add dev phy0.1-ap0 parent 1: protocol all basic match "cmp(u16 at 12 mask 0xffff eq 0x88b6)" flowid 1:10 2>&1 | head -n 2
echo "--- filters ---"
tc filter show dev phy0.1-ap0 | head -n 8'
