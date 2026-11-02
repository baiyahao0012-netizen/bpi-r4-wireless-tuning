#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== link health ==="
iw dev phy0.0-sta0 link 2>/dev/null | head -6
echo "=== ping at full power ==="
ping -c 10 -W 2 192.168.3.1 2>&1 | tail -3
echo "=== arp ==="
ip neigh | head -5
echo "=== event on/off + count ==="
echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
echo > /sys/kernel/debug/tracing/trace
ping -c 10 -W 2 192.168.3.1 >/dev/null 2>&1
sleep 1
echo "events=$(grep -c wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null)"
echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
