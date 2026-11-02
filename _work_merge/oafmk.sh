#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
P=$SDK/package/OpenAppFilter/open-app-filter
echo "=== oaf.ko present in package? ==="
find $P -name "*.ko" -o -name "*.bin" -o -name "*.o" | head -10
echo "=== src listing (all) ==="
ls -la $P/src/ | head -40
echo "=== open-app-filter/Makefile ==="
cat $P/Makefile
echo "=== src/Makefile ==="
cat $P/src/Makefile | head -60
echo DONE
