#!/bin/sh
# MCS 掩码实时调整验证：锁定全层最低速率 -> 回读 -> 恢复 -> 回读
echo "== lock =="
iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0
sleep 3
echo "== locked station =="
iw station get 90:de:80:1c:6a:7a
echo "== restore =="
iw dev phy0.1-ap0 set bitrates
sleep 1
echo "== restored station =="
iw station get 90:de:80:1c:6a:7a
