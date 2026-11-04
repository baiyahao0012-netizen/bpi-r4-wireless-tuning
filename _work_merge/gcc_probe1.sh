#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
echo '=== tracing available_tracers / events of interest ==='
$S 'cat /sys/kernel/debug/tracing/available_tracers' 2>/dev/null
$S 'ls /sys/kernel/debug/tracing/events/mac80211/ 2>/dev/null | tr "\n" " "' 2>/dev/null
echo
$S 'ls /sys/kernel/debug/tracing/events/ 2>/dev/null | tr "\n" " "' 2>/dev/null
echo
echo '=== sta debugfs (mac80211 per-sta stats) ==='
$S 'ls /sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-sta0/stations/*/ 2>/dev/null | tr "\n" " "' 2>/dev/null
echo
echo '=== aql / airtime / queue stats in mt76 debugfs ==='
$S 'ls /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats /sys/kernel/debug/ieee80211/phy0/mt76/xmit-queues 2>/dev/null' 2>/dev/null
$S 'cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats 2>/dev/null | head -20' 2>/dev/null
echo A_DONE
