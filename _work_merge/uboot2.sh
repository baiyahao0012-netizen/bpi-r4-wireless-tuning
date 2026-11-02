#!/bin/bash
BR=/root/src/openwrt-24.10.0
P=$BR/package/boot/uboot-mediatek/patches/450-add-bpi-r4.patch
echo "=== LZMA / GZIP / ZSTD / BZIP2 in bpi-r4 u-boot patch ==="
grep -n "CONFIG_LZMA\|CONFIG_GZIP\|CONFIG_ZSTD\|CONFIG_BZIP2\|CONFIG_LZO\|CONFIG_SPL_LZMA" $P | head -30
echo "=== U-Boot defconfig names for bpi-r4 ==="
grep -n "^+++ b/configs/" $P | head -20
echo "=== check uboot source configs dir if present ==="
ls $BR/package/boot/uboot-mediatek/ 2>&1
find / -maxdepth 4 -name "mt7988*" -path "*uboot*" 2>/dev/null | head
echo "=== read U-Boot from board SD (bl31-uboot at 6656k) and search lzma ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'dd if=/dev/mmcblk0 bs=1M skip=6656 count=2 2>/dev/null | strings | grep -iE "lzma|zstd|gzip|bzip2" | sort -u | head -20' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo "=== also search whole uboot region for FIT decompress strings ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'dd if=/dev/mmcblk0 bs=1M skip=6656 count=1 2>/dev/null | strings | grep -iE "Uncompressing|lzma_dec|zstd_dec|gzip_dec|LZMA" | head -20' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo DONE
