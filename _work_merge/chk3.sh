#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- /proc/modules lines ---"
wc -l < /proc/modules
echo "--- /sys/module entries ---"
ls /sys/module/ | wc -l
ls /sys/module/ | head -30
echo "--- dmesg tail ---"
dmesg | tail -30
echo "--- logread tail ---"
logread 2>/dev/null | tail -20
echo "--- modules.d ---"
ls /etc/modules.d/ 2>&1
echo "--- modprobe test ---"
modprobe cfg80211 2>&1; echo "rc=$?"
dmesg | tail -5
' 2>/dev/null
