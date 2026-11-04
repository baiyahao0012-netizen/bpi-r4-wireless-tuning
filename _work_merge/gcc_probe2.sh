#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
echo '=== per-STA mac80211 stats ==='
$S 'STA=$(ls /sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-sta0/stations/ 2>/dev/null | head -1); echo "sta=$STA"; ls /sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-sta0/stations/$STA/ 2>/dev/null | tr "\n" " "' 2>/dev/null
echo
echo '=== sta_flags / aql / airtime ==='
$S 'STA=$(ls /sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-sta0/stations/ 2>/dev/null | head -1); D=/sys/kernel/debug/ieee80211/phy0/netdev:phy0.0-sta0/stations/$STA; echo "--sta_flags--"; cat $D/sta_flags 2>/dev/null; echo "--aql len--"; cat $D/aql 2>/dev/null | head -3; echo "--airtime--"; cat $D/airtime 2>/dev/null | head -3; echo "--rx_stats--"; cat $D/rx_duration 2>/dev/null | head -3' 2>/dev/null
echo '=== mt76 tx_stats ==='
$S 'cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats 2>/dev/null | head -25' 2>/dev/null
echo '=== xmit-queues (aqm) ==='
$S 'cat /sys/kernel/debug/ieee80211/phy0/mt76/xmit-queues 2>/dev/null | head -20' 2>/dev/null
echo B_DONE
