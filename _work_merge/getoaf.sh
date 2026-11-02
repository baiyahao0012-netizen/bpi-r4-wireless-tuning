#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat /root/oaf.ko' 2>/dev/null > /root/oaf.ko
ls -la /root/oaf.ko
md5sum /root/oaf.ko
RD=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
echo "=== oaf.ko this_module size ==="
$RD -SW /root/oaf.ko 2>/dev/null | grep -i this_module
echo "=== vermagic ==="
strings -a /root/oaf.ko | grep -i "6.6.73" | head -3
echo "=== .modinfo ==="
$RD -p .modinfo /root/oaf.ko 2>/dev/null | head
echo DONE
