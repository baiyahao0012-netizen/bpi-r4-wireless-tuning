#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== board U-Boot version ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'strings /sys/firmware/devicetree/base/chosen/u-boot,version; echo; strings /sys/firmware/devicetree/base/chosen/bootargs; echo; strings /sys/firmware/devicetree/base/chosen/rootdisk' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo "=== uboot-mediatek package ==="
ls $BR/package/boot/uboot-mediatek/ 2>&1
echo "=== find mt7988 u-boot configs ==="
ls $BR/package/boot/uboot-mediatek/*mt7988* 2>&1
echo "=== grep LZMA in uboot-mediatek files ==="
grep -rn "LZMA\|GZIP\|BZIP2\|ZSTD" $BR/package/boot/uboot-mediatek/ 2>/dev/null | head -20
echo "=== grep LZMA in mt7988 defconfig ==="
find $BR/package/boot/uboot-mediatek -name "*mt7988*" | head -20
echo DONE
