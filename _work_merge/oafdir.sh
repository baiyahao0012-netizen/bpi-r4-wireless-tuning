#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== SDK OpenAppFilter/oaf ==="
find $SDK/package/OpenAppFilter/oaf -type f 2>/dev/null | head -30
echo "=== /root/oaf-pinned/oaf ==="
find /root/oaf-pinned -type f 2>/dev/null | head -40
echo "=== getoaf.sh ==="
cat /root/getoaf.sh 2>/dev/null | head -30
echo "=== oaf3.sh ==="
head -30 /root/oaf3.sh 2>/dev/null
echo "=== oaf4.sh ==="
head -30 /root/oaf4.sh 2>/dev/null
echo "=== search whole SDK for oaf.ko or kmod-oaf ==="
find /root/sdk -iname "*kmod*oaf*" -o -iname "oaf.ko" 2>/dev/null | head -10
echo DONE
