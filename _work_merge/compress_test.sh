#!/bin/bash
NEW=/root/kbuild/linux-6.6.73
IMG=$NEW/arch/arm64/boot/Image
echo "=== raw Image size ==="
stat -c %s $IMG
echo "=== gzip -9 ==="
gzip -9 -c $IMG | wc -c
echo "=== gzip -9 (OpenWrt libdeflate -12 style) ==="
gzip -9 -n -c $IMG | wc -c
echo "=== lzma -9 ==="
xz --format=lzma -9 -c $IMG 2>/dev/null | wc -c
echo "=== xz -9 ==="
xz -9 -c $IMG 2>/dev/null | wc -c
echo "=== zstd -19 ==="
zstd -19 -c $IMG 2>/dev/null | wc -c
echo "=== zstd -22 ==="
zstd -22 -c $IMG 2>/dev/null | wc -c
echo "=== old kernel compressed size (gzip) = 5633434 ==="
echo "=== board U-Boot version ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'ls /sys/firmware/devicetree/base/chosen/; cat /sys/firmware/devicetree/base/chosen/u-boot,version 2>/dev/null; echo; ls /sys/firmware/devicetree/base/ | head -20' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo DONE
