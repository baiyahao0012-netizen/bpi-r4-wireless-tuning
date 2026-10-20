#!/bin/sh
CAP=/sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap
echo "== write test =="
echo 8 > "$CAP" 2>&1
echo "rc=$?"
echo "== read after write =="
cat "$CAP" 2>&1
echo "== dmesg agg_win_cap =="
dmesg | tail -30 | grep -i agg
echo "== also check dmesg recent errors =="
dmesg | tail -10
echo "== other mt76 nodes =="
cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats 2>&1 | head -5
