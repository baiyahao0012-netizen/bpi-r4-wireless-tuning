#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd /root/fitparts
dd if=/root/p7.img of=fit.dtb bs=1 count=4096 2>/dev/null
ls -la fit.dtb
xxd -l 16 fit.dtb
echo "=== dtc available? ==="
which dtc fdtget 2>&1
ls $SDK/staging_dir/host/bin/ | grep -iE "^dtc|fdt" 2>&1
echo "=== dump FIT structure ==="
DTC=$SDK/staging_dir/host/bin/dtc
if [ -x "$DTC" ]; then $DTC -I dtb -O dts fit.dtb 2>&1 | head -120; else echo "no dtc"; fi
echo DONE
