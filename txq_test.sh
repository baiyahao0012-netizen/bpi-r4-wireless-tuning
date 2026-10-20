#!/bin/sh
# 软件队列 DRR 参数实时调整验证
echo "== txq before =="
iw phy0 get txq
echo "== hw-queues before =="
cat /sys/kernel/debug/ieee80211/phy0/mt76/hw-queues
echo "== set quantum 512 =="
iw phy0 set txq quantum 512
iw phy0 get txq
echo "== set quantum 65535 =="
iw phy0 set txq quantum 65535
iw phy0 get txq
echo "== hw-queues after =="
cat /sys/kernel/debug/ieee80211/phy0/mt76/hw-queues
echo TXQ_DONE
