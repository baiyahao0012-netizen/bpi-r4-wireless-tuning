#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== pad-rootfs definition ==="
grep -rn "define Build/pad-rootfs" -A8 $BR/include/*.mk
echo "=== external-with-rootfs / fit definition ==="
grep -rn "define Build/fit" -A30 $BR/include/image-commands.mk
echo "=== external-with-rootfs in fit.sh ==="
find $BR -name "fit.sh" -path "*image*" -o -name "fit.sh" | head
cat $BR/scripts/fit.sh 2>/dev/null | head -60
echo "=== SDK config ROOTFS_PARTSIZE ==="
grep -n "ROOTFS_PARTSIZE\|ROOTFS_SQUASHFS\|ROOTFS_BLOCK" /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/.config
echo DONE
