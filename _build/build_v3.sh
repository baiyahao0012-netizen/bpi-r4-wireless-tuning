#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PATCHDIR=$SDK/package/kernel/mt76/patches
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6

echo "=== 1. Force reset ==="
rm -rf "$TREE"
rm -f "$PATCHDIR/999"*

echo "=== 2. Prepare (pristine) ==="
make -C "$SDK" package/kernel/mt76/prepare V=s 2>&1 | tail -3
grep -r agg_win_cap "$TREE/mt7996/" 2>/dev/null | head -3 && echo "FAIL: NOT pristine" || echo "OK: pristine confirmed"

echo "=== 3. Apply v2_final (CPTCFG_ fix + fops before #ifdef) ==="
cp '/mnt/d/Desktop/AI 辅助对话/_build/apply_v2_final.py' /root/apply_v2_final.py
python3 /root/apply_v2_final.py "$TREE"

echo "=== 4. Verify patched tree ==="
echo "  mt7996.h  : $(grep -c agg_win_cap "$TREE/mt7996/mt7996.h") lines"
echo "  mcu.c     : $(grep -c agg_win_cap "$TREE/mt7996/mcu.c") lines"
echo "  debugfs.c : $(grep -c agg_win_cap "$TREE/mt7996/debugfs.c") lines"
echo "  fops #ifdef: $(grep -c 'CPTCFG_MAC80211_DEBUGFS' "$TREE/mt7996/debugfs.c") lines"
# Check: fops body should be BEFORE the #ifdef line
IFDEF_LINE=$(grep -n '#if defined(CONFIG_MAC80211_DEBUGFS)' "$TREE/mt7996/debugfs.c" | head -1 | cut -d: -f1)
READ_LINE=$(grep -n 'mt7996_agg_win_cap_read' "$TREE/mt7996/debugfs.c" | head -1 | cut -d: -f1)
echo "  #ifdef line: $IFDEF_LINE, read func line: $READ_LINE"
if [ "$READ_LINE" -lt "$IFDEF_LINE" ]; then echo "OK: fops BEFORE #ifdef (will compile)"; else echo "WARN: fops AFTER #ifdef (may be skipped)"; fi

echo "=== 5. Compile ==="
make -C "$SDK" package/kernel/mt76/compile V=s -j24 > /root/mt76_build_v8.log 2>&1 || true

echo "=== 6. Result ==="
KO=$TREE/mt7996/mt7996e.ko
if [ -f "$KO" ]; then
  echo "KO OK $(md5sum "$KO" | cut -d' ' -f1)"
  echo "=== strings check ==="
  strings "$KO" | grep -i agg_win_cap
  echo "=== nm check ==="
  nm "$KO" 2>/dev/null | grep -iE 'agg_win_cap_read|agg_win_cap_write|fops_agg_win_cap'
else
  echo "KO MISSING"
  grep -E 'error:|undefined' /root/mt76_build_v8.log | head -15
fi
