#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== tools ==="
for t in nft iptables iperf3 iperf nc socat python3 perl; do command -v $t >/dev/null 2>&1 && echo "$t: $(command -v $t)" || echo "$t: -"; done
echo "=== tracing_on ==="
cat /sys/kernel/debug/tracing/tracing_on
echo "=== try nft DSCP marking ==="
nft add table inet dsctest 2>&1
nft add chain inet dsctest out "{ type route hook output priority mangle; }" 2>&1
nft add rule inet dsctest out ip protocol icmp ip dscp set af41 2>&1
nft list table inet dsctest 2>&1 | head -10
echo "=== enable event + ping ==="
echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
echo > /sys/kernel/debug/tracing/trace
ping -c 10 -W 1 192.168.3.1 >/dev/null 2>&1; echo "ping rc=$?"
sleep 1
echo "events: $(grep -c wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null)"
grep wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null | head -6
echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
nft delete table inet dsctest 2>&1
' 2>&1 | grep -v "WARNING|post-quantum|store now|upgraded|openssh.com"
