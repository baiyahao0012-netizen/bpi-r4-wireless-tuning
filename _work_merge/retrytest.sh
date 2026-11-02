#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== current txpower ==="
iw dev phy0.0-sta0 info 2>/dev/null | grep -i txpower
echo "=== enable event ==="
echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
echo > /sys/kernel/debug/tracing/trace
echo "=== lower txpower to 1 dBm to force retries ==="
iw dev phy0.0-sta0 set txpower fixed 100 2>&1
sleep 2
iw dev phy0.0-sta0 info 2>/dev/null | grep -i txpower
ping -c 25 -W 2 -i 0.3 192.168.3.1 >/dev/null 2>&1; echo "ping rc=$?"
sleep 1
echo "=== retry distribution (all wifi_dscp events) ==="
grep wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null | grep -oE "retry=[0-9]+" | sort | uniq -c
echo "=== ACK events with retry>0 ==="
grep wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null | grep "stage=2" | grep -vE "retry=0" | head -8
echo "=== total events ==="
grep -c wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null
echo "=== restore txpower ==="
iw dev phy0.0-sta0 set txpower auto 2>&1
sleep 2
iw dev phy0.0-sta0 info 2>/dev/null | grep -i txpower
echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
' 2>&1 | grep -v "WARNING|post-quantum|store now|upgraded|openssh.com"
