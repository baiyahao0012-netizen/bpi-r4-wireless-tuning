#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
P=$SDK/package/OpenAppFilter
echo "=== tree (top) ==="
ls -la $P/
echo "=== open-app-filter ==="
find $P/open-app-filter -type f | head -40
echo "=== .c/.h/.ko files anywhere in OpenAppFilter ==="
find $P -name "*.c" -o -name "*.h" -o -name "*.ko" | head -30
echo "=== Makefile ==="
cat $P/open-app-filter/Makefile 2>/dev/null | head -60
echo "=== /root/oaf-pinned ==="
ls -la /root/oaf-pinned/ /root/oaf-pinned/oaf 2>/dev/null | head -30
echo DONE
