#!/bin/bash
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@192.168.240.1"
$SSH '
echo "=== cmdline ==="; cat /proc/cmdline
echo "=== mounts ==="; cat /proc/mounts
echo "=== df -h ==="; df -h
echo "=== fitblk devices ==="; ls -la /dev/fit* 2>/dev/null; cat /sys/class/block/fit0/size 2>/dev/null; cat /sys/class/block/fitrw/size 2>/dev/null
echo "=== rom ==="; ls /rom | head -5; ls -la /rom/ 2>/dev/null | head -3
echo "=== overlay upper ==="; ls /overlay | head
echo "=== modules dir ==="; ls -la /lib/modules/6.6.73/ | head -20
echo "=== kernel modules loaded ==="; lsmod | head -20
' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo BOARD_DONE
