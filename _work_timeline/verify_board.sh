#!/bin/sh
echo "== md5 =="
md5sum /lib/modules/6.6.73/mt7996e.ko
echo "== agg_win_cap =="
find /sys/kernel/debug/ieee80211 -name agg_win_cap 2>/dev/null
cat /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap 2>&1
echo "== APs =="
iwinfo | grep -E 'ESSID|Channel'
echo "== stations =="
iw dev phy0.1-ap0 station dump | grep -E '^Station|rx bytes|tx bitrate' | head
echo "== iperf3 =="
pidof iperf3 || (iperf3 -s -p 5201 -D && echo "iperf3 started")
echo DONE
