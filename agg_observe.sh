#!/bin/sh
# A-MPDU 聚合状态观察：打流中读取聚合/队列统计
echo "== station agg_status =="
cat /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/90:de:80:1c:6a:7a/agg_status
echo "== station flags =="
cat /sys/kernel/debug/ieee80211/phy0/netdev:phy0.1-ap0/stations/90:de:80:1c:6a:7a/flags
echo "== mt76 tx_stats =="
cat /sys/kernel/debug/ieee80211/phy0/mt76/tx_stats
echo "== mt76 xmit-queues =="
cat /sys/kernel/debug/ieee80211/phy0/mt76/xmit-queues
echo "== mt76 hw-queues =="
cat /sys/kernel/debug/ieee80211/phy0/mt76/hw-queues
echo AGG_DONE
