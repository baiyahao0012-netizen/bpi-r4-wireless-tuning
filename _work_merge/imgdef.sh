#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== mediatek image files ==="
ls $BR/target/linux/mediatek/image/ 2>&1
echo "=== bpi-r4-poe image definition ==="
grep -n -A40 "bananapi_bpi-r4-poe" $BR/target/linux/mediatek/image/filogic.mk 2>/dev/null | head -70
echo "=== FIT-related build definitions ==="
grep -rn "fit\|FIT" $BR/target/linux/mediatek/image/Makefile 2>/dev/null | head -30
echo "=== board /lib/upgrade/fit.sh ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat /lib/upgrade/fit.sh' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo DONE
