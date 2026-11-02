#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- tracefs ---"
ls -la /sys/kernel/tracing/ 2>&1 | head -15
echo "--- mount trace ---"
mount | grep -iE "trace|debugfs" 2>&1
echo "--- /sys/kernel/debug/tracing ---"
ls /sys/kernel/debug/tracing/ 2>&1 | head -5
echo "--- proc/filesystems ---"
grep -i trace /proc/filesystems 2>&1
echo "--- dmesg trace ---"
dmesg | grep -iE "trace|ftrace" | head -10
echo "--- modules ---"
lsmod | head -20
echo "--- overlay intact ---"
ls /overlay/upper/ 2>&1 | head
df -h /overlay /rom / 2>&1
' 2>/dev/null
