#!/bin/sh
# MCS 实时调整主实验：打流中锁 vht-mcs-5 1:0（NSS1 低速率）-> 回读 -> 恢复 -> 回读
echo "T0 lock"
iw dev phy0.1-ap0 set bitrates vht-mcs-5 1:0
sleep 5
echo "T5 locked station:"
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
sleep 15
echo "T20 restore"
iw dev phy0.1-ap0 set bitrates
sleep 3
echo "T23 restored station:"
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
echo MCS_DONE
