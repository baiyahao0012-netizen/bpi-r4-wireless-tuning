#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== routes ==="
ip route | head
echo "=== sta iface ==="
ip -4 addr show phy0.0-sta0 2>/dev/null | head -5
echo "=== ping DSCP support ==="
ping -h 2>&1 | grep -iE "\-Q|tos" | head -3
echo "=== enable event and count ==="
echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
echo "enabled=$(cat /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable)"
ping -c 5 -W 1 -Q 0x88 192.168.3.1 >/dev/null 2>&1
echo "ping rc=$?"
sleep 1
grep -c wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null
echo "--- sample ---"
grep wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null | head -5
echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
' 2>&1 | grep -v "WARNING|post-quantum|store now|upgraded|openssh.com"
