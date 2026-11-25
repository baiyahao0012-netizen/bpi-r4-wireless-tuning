#!/bin/bash
AP=192.168.240.1
echo 12345678 | sudo -S pkill -x iperf3 2>/dev/null
sleep 1
iperf3 -s -B 192.168.240.126 -p 5204 -D
sleep 1
ss -lnt 2>/dev/null | grep 5204 || echo NO_LISTEN
echo "=== UDP 100M AP->Pi ==="
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@$AP \
  'iperf3 -c 192.168.240.126 -u -b 100M -t 10 -p 5204 2>&1 | tail -n 4'
echo "=== UDP 200M AP->Pi ==="
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@$AP \
  'iperf3 -c 192.168.240.126 -u -b 200M -t 10 -p 5204 2>&1 | tail -n 4'
echo 12345678 | sudo -S pkill -x iperf3 2>/dev/null
echo THROUGHPUT_DONE
