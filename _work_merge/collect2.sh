#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=/root/kbuild/linux-6.6.73
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic
STAGE=/root/modstage/lib/modules/6.6.73
rm -rf /root/modstage; mkdir -p $STAGE

echo "=== kernel modules from board list ==="
while read m; do
  case "$m" in cfg80211.ko|mac80211.ko|compat.ko|mt76.ko|mt76-connac-lib.ko|mt7996e.ko) continue;; esac
  f=$(find $KD -name "$m" -not -path "*/.tmp_versions/*" 2>/dev/null | head -1)
  [ -n "$f" ] && cp -f "$f" "$STAGE/$m"
done < /root/board_mods.txt
echo "after kernel: $(ls $STAGE/*.ko 2>/dev/null | wc -l)"

echo "=== gpio-button-hotplug ==="
f=$(find $BD -path "*gpio-button-hotplug*" -name "gpio-button-hotplug.ko" 2>/dev/null | head -1)
if [ -n "$f" ]; then cp -f "$f" "$STAGE/"; echo "  from $f"; else echo "  NOT BUILT YET"; fi

echo "=== backports: mac80211 pkg ==="
for m in cfg80211.ko compat.ko mac80211.ko; do
  f=$(find $BD/mac80211-regular -path "*.pkgdir*" -name "$m" 2>/dev/null | head -1)
  if [ -n "$f" ]; then cp -f "$f" "$STAGE/$m"; echo "  + $m  $(stat -c %s $f)"; else echo "  MISSING $m"; fi
done

echo "=== mt76 ==="
MT=$(ls -d $BD/mt76-2025.01.14~8e4f72b6 2>/dev/null)
for m in mt76.ko mt76-connac-lib.ko; do
  f=$(find $MT -maxdepth 1 -name "$m" 2>/dev/null | head -1)
  if [ -n "$f" ]; then cp -f "$f" "$STAGE/$m"; echo "  + $m  $(stat -c %s $f)"; else echo "  MISSING $m"; fi
done
f=$(find $MT/mt7996 -name "mt7996e.ko" 2>/dev/null | head -1)
if [ -n "$f" ]; then cp -f "$f" "$STAGE/mt7996e.ko"; echo "  + mt7996e.ko  $(stat -c %s $f)"; else echo "  MISSING mt7996e.ko"; fi

echo "=== final ==="
echo "count: $(ls $STAGE/*.ko 2>/dev/null | wc -l) (board needs 103)"
du -sh $STAGE
echo "--- missing vs board list ---"
while read m; do [ -f "$STAGE/$m" ] || echo "MISSING $m"; done < /root/board_mods.txt
echo COLLECT_DONE
