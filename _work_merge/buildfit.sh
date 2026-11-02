#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BR=/root/src/openwrt-24.10.0
KD=/root/kbuild/linux-6.6.73
MK=$SDK/staging_dir/host/bin/mkimage
TARGET=$((0x1032000))
cd /root/fitparts

zstd -19 -q -c $KD/arch/arm64/boot/Image > Image.zst
echo "kernel.zst size: $(stat -c %s Image.zst)"

build() {
  $BR/scripts/mkits.sh -D bananapi_bpi-r4-poe -o new.its -k Image.zst -C zstd \
    -d fdt-1.dtb -r rootfs.pad \
    -a 0x46000000 -e 0x46000000 -s 0x45f00000 \
    -O mt7988a-bananapi-bpi-r4-emmc:dtbo-emmc.dtbo \
    -O mt7988a-bananapi-bpi-r4-rtc:dtbo-rtc.dtbo \
    -O mt7988a-bananapi-bpi-r4-sd:dtbo-sd.dtbo \
    -O mt7988a-bananapi-bpi-r4-wifi-mt7996a:dtbo-wifi.dtbo \
    -c config-mt7988a-bananapi-bpi-r4-poe -A arm64 -v 6.6.73 > /dev/null 2>&1
  $MK -E -B 0x1000 -f new.its new.itb > /dev/null 2>&1
}

PAD=0
for i in 1 2 3 4; do
  cp rootfs.squashfs rootfs.pad
  [ $PAD -gt 0 ] && dd if=/dev/zero bs=1 count=$PAD >> rootfs.pad 2>/dev/null
  build
  SZ=$(stat -c %s new.itb)
  echo "iter $i: pad=$PAD fit=$SZ target=$TARGET"
  if [ "$SZ" -eq "$TARGET" ]; then echo "== MATCH =="; break; fi
  D=$((TARGET - SZ))
  PAD=$((PAD + D))
  PAD=$(( (PAD / 4096) * 4096 ))
done
echo "=== final ==="
ls -la new.itb
echo "=== mkimage -l ==="
$MK -l new.itb 2>&1 | grep -E "Image [0-9]|Compression|Data Size|Data Offset|Description" | head -50
echo DONE
