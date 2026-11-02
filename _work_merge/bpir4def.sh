#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== bananapi_bpi-r4-common definition ==="
grep -n -B2 -A40 "define Device/bananapi_bpi-r4-common" $BR/target/linux/mediatek/image/filogic.mk
echo "=== fit.mk (image build macro) ==="
find $BR -name "fit*.sh" -o -name "*fit*.mk" | head
echo "=== scripts/fit*.sh ==="
ls $BR/scripts/ | grep -i fit
echo DONE
