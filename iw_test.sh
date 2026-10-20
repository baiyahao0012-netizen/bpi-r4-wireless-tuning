#!/bin/sh
# 验证 iw 各命令形式
echo "== A: iw dev info =="
iw dev phy0.1-ap0 info
echo "== B: iw station dump (省略dev) =="
iw station dump
echo "== C: iw dev station dump =="
iw dev phy0.1-ap0 station dump
echo "== D: iw dev station get =="
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
echo "== E: lock bitrates =="
iw dev phy0.1-ap0 set bitrates legacy-5 6 ht-mcs-5 0 vht-mcs-5 1:0 he-mcs-5 1:0
echo LOCK_DONE
echo "== F: get after lock =="
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
echo "== G: restore =="
iw dev phy0.1-ap0 set bitrates
echo RESTORE_DONE
echo "== H: get after restore =="
iw dev phy0.1-ap0 station get 90:de:80:1c:6a:7a
