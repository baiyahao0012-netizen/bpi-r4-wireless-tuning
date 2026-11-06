#!/bin/sh
D=/sys/kernel/debug/ieee80211/phy0
echo "=== station dump (full) ==="
iw dev phy0.1-ap0 station dump
echo "=== tx_stats head ==="
head -30 $D/mt76/tx_stats
