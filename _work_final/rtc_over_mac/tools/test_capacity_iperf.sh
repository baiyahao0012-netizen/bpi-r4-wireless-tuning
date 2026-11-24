#!/bin/bash
# Runs on Pi. True link capacity via iperf3 UDP from AP (C tool, can saturate).
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
pkill -f "iperf3 -s" 2>/dev/null; sleep 1
iperf3 -s -B 192.168.240.126 -p 5201 -D
sleep 1
echo "=== UDP 200M offered, 15s ==="
$A 'iperf3 -c 192.168.240.126 -u -b 200M -t 15 -p 5201 2>&1 | tail -n 3'
echo "=== UDP 400M offered, 15s ==="
$A 'iperf3 -c 192.168.240.126 -u -b 400M -t 15 -p 5201 2>&1 | tail -n 3'
pkill -f "iperf3 -s" 2>/dev/null
echo CAP2_DONE
