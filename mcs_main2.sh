#!/bin/sh
# MCS 全层锁主实验：打流中全层锁最低速率 -> 回读 -> 恢复 -> 回读
echo "T0 lockall"
iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0
sleep 5
echo "T5 locked station:"
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
sleep 10
echo "T15 restore"
iw dev phy0.1-ap0 set bitrates
sleep 3
echo "T18 restored station:"
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
echo MCS2_DONE
