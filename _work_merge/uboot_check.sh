#!/bin/bash
KD=/root/kbuild/linux-6.6.73
echo "=== minimal kernel compressed sizes ==="
echo -n "raw: "; stat -c %s $KD/arch/arm64/boot/Image
echo -n "gzip -9: "; gzip -9 -c $KD/arch/arm64/boot/Image | wc -c
echo -n "zstd -19: "; zstd -19 -q -c $KD/arch/arm64/boot/Image 2>/dev/null | wc -c
echo -n "zstd -22: "; zstd -22 -q -c $KD/arch/arm64/boot/Image 2>/dev/null | wc -c
echo -n "lzma -9: "; xz --format=lzma -9 -c $KD/arch/arm64/boot/Image 2>/dev/null | wc -c
echo "old kernel gzip = 5633434"

echo "=== read U-Boot region from board SD ==="
mkdir -p /root/uboot
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'dd if=/dev/mmcblk0 bs=1M skip=6656 count=6 2>/dev/null' > /root/uboot/uboot_region.bin 2>/dev/null
ls -la /root/uboot/uboot_region.bin
echo "=== search decompressor strings ==="
for pat in lzma LZMA zstd ZSTD zlib gzip bzip2 lzo "Uncompressing" "Uncompressing Kernel" "lzma_dec" "zstd_dec" "gzip_dec" "decompress"; do
  n=$(strings -a /root/uboot/uboot_region.bin 2>/dev/null | grep -c "$pat")
  echo "$pat -> $n"
done
echo "=== sample matching strings ==="
strings -a /root/uboot/region.bin 2>/dev/null | head -0
strings -a /root/uboot/uboot_region.bin 2>/dev/null | grep -iE "lzma|zstd|Uncompress" | sort -u | head -20
echo DONE
