#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
O=$SDK/package/OpenAppFilter/oaf
echo "=== oaf/Makefile ==="
cat $O/Makefile
echo "=== oaf/src/Makefile ==="
cat $O/src/Makefile
echo "=== module name / license / depends in fwx_main.c ==="
grep -nE "MODULE_(LICENSE|AUTHOR|DESCRIPTION|VERSION|ALIAS)|module_init|module_exit" $O/src/fwx_main.c | head -12
echo "=== is package in SDK .config? ==="
grep -E "OpenAppFilter|PACKAGE_oaf|PACKAGE_appfilter" $SDK/.config | head -10
echo "=== oaf dir listing ==="
ls -la $O/
echo DONE
