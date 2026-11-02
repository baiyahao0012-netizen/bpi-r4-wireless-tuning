#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=/root/kbuild/linux-6.6.73
STAGE=/root/modstage/lib/modules/6.6.73
rm -rf /root/modstage
mkdir -p $STAGE

echo "=== 1. kernel modules ==="
find $KD -name "*.ko" -not -path "*/.tmp_versions/*" | while read f; do
  cp -f "$f" "$STAGE/$(basename $f)"
done
echo "kernel ko: $(ls $STAGE/*.ko 2>/dev/null | wc -l)"

echo "=== 2. backports (mac80211 pkg) ==="
find $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular -path "*.pkgdir*" -name "*.ko" 2>/dev/null | while read f; do
  cp -f "$f" "$STAGE/$(basename $f)"
  echo "  + $(basename $f)"
done
echo "after backports: $(ls $STAGE/*.ko 2>/dev/null | wc -l)"

echo "=== 3. mt76 ==="
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
find $TREE -maxdepth 2 -name "*.ko" 2>/dev/null | while read f; do
  cp -f "$f" "$STAGE/$(basename $f)"
  echo "  + $(basename $f)"
done

echo "=== totals ==="
ls $STAGE/*.ko 2>/dev/null | wc -l
du -sh $STAGE
echo "=== key modules ==="
for m in mac80211 cfg80211 compat mt76 mt76-connac-lib mt7996e; do
  if [ -f "$STAGE/$m.ko" ]; then echo "$m.ko $(stat -c %s $STAGE/$m.ko) $(md5sum $STAGE/$m.ko | cut -d' ' -f1)"; else echo "$m.ko MISSING"; fi
done
echo "=== vs board /rom list ==="
echo "rom ko count = 71"
echo COLLECT_DONE
