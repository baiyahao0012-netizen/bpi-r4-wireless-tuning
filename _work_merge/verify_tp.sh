#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== which modules failed ==="
dmesg | grep "section size must match" | sed "s/.*module //;s/:.*//" | sort -u
echo "=== wifi_dscp present? ==="
ls /sys/kernel/debug/tracing/events/mac80211/ | grep -i dscp
echo "--- format ---"
cat /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/format 2>&1
echo "=== iw dev ==="
iw dev 2>&1 | head -30
echo "=== iwinfo ==="
iwinfo 2>&1 | head -20
' 2>/dev/null
