#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== kernel ==="
uname -a
echo "=== struct module errors in dmesg? ==="
dmesg | grep -c "section size must match"
echo "=== loaded modules ==="
wc -l < /proc/modules
cat /proc/modules | awk "{print \$1}" | tr "\n" " "
echo
echo "=== mac80211 tracepoint ==="
ls /sys/kernel/debug/tracing/events/mac80211/ 2>&1
echo "=== wifi_dscp format ==="
cat /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/format 2>&1 | head -20
echo "=== iw dev ==="
iw dev 2>&1 | head -25
echo "=== overlay ==="
df -h /overlay
' 2>/dev/null
