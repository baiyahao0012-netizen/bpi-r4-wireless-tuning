#!/bin/sh
# v2_verify.sh — board-side end-to-end verification of agg_win_cap driver
echo "=== 1. Driver MD5 ==="
md5sum /lib/modules/6.6.73/mt7996e.ko
echo "=== 2. Node existence ==="
ls -la /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap 2>&1
echo "=== 3. Write test ==="
echo 8 > /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap 2>&1
RC=$?; echo "write rc=$RC"
echo "=== 4. Read test ==="
cat /sys/kernel/debug/ieee80211/phy0/mt76/agg_win_cap 2>&1
echo "=== 5. dmesg agg_win_cap ==="
dmesg | grep agg_win_cap | tail -20
echo "=== 6. APs & stations ==="
iwinfo | grep ESSID
iw dev phy0.1-ap0 station dump | grep -E '^Station'
echo "=== 7. iperf3 server ==="
pidof iperf3 || (iperf3 -s -p 5201 -D && echo STARTED)
echo "DONE"
