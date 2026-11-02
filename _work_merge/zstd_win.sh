#!/bin/bash
BR=/root/src/openwrt-24.10.0
KD=/root/kbuild/linux-6.6.73
IMG=$KD/arch/arm64/boot/Image
echo "=== OpenWrt uses fit zstd anywhere? ==="
grep -rn "fit zstd\|zstd | fit\|fit lzma" $BR/include/ $BR/target/linux/mediatek/image/ 2>/dev/null | head -10
echo "=== Build/fit definition ==="
grep -n -A20 "^define Build/fit" $BR/include/image.mk | head -30
echo
echo "=== zstd sizes at various windows ==="
for w in 19 20 21 22 23; do
  printf "wlog=%s: " $w
  zstd -19 --zstd=wlog=$w -q -c $IMG 2>/dev/null | wc -c
done
echo "default -19: $(zstd -19 -q -c $IMG 2>/dev/null | wc -c)"
echo "default -22: $(zstd -22 -q -c $IMG 2>/dev/null | wc -c)"
echo "old kernel gzip = 5633434"
echo "=== zstd version ==="
zstd --version
echo DONE
