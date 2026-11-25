#!/bin/bash
IF=wlan0
AP=192.168.240.1
echo "=== preflight ==="; IFACE=$IF bash /tmp/preflight.sh 2>&1 | tail -n 1
echo 12345678 | sudo -S pkill -x iperf3 2>/dev/null
sleep 1
iperf3 -s -B 192.168.240.126 -p 5203 -D
sleep 1
echo "=== 后台 ping 20s ==="
( ping -I $IF -c 100 -i 0.2 -W 1 $AP 2>&1 | tail -n 2 > /tmp/ping_load.txt ) &
sleep 1
echo "=== AP -> Pi UDP 100M 10s ==="
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@$AP \
  'iperf3 -c 192.168.240.126 -u -b 100M -t 10 -p 5203 2>&1 | tail -n 2'
wait
echo "=== 负载期间 ping ==="; cat /tmp/ping_load.txt
echo "=== link ==="; /sbin/iw dev $IF link 2>/dev/null | grep -E 'signal|bitrate' | head -n 3
echo "=== USB 新事件 ==="; dmesg | tail -n 15 | grep -iE 'usb.*disconnect|reset high|mt7921.*timeout' || echo none
echo 12345678 | sudo -S pkill -x iperf3 2>/dev/null
echo LOAD_TEST_DONE
