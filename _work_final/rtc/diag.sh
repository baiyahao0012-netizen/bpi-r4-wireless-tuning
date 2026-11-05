#!/bin/sh
D=/sys/kernel/debug/ieee80211/phy0
echo "D=$D"
S=$(ls -d $D/netdev:phy0.1-ap0/stations/* 2>/dev/null | head -1)
echo "S=$S"
echo "--- aql_pending ---"
cat $D/aql_pending 2>&1 | head -2
echo "--- sta aql ---"
cat "$S/aql" 2>&1 | head -2
echo "--- airtime ---"
cat "$S/airtime" 2>&1 | head -2
echo "--- tx_stats ---"
grep -E "Tx attempts|Tx success" $D/mt76/tx_stats 2>&1 | head -2
