#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6

echo "=== 1. Pristine check ==="
count=$(grep -rc agg_win_cap "$TREE/mt7996/" 2>/dev/null | head -1 | cut -d: -f2)
echo "  agg_win_cap count in mt7996/: $count (expect 0)"

echo "=== 2. Apply v2 Python patch ==="
python3 /root/apply_v2_direct.py "$TREE"

echo "=== 3. Verify patched tree ==="
echo "  mt7996.h  : $(grep -c agg_win_cap "$TREE/mt7996/mt7996.h") lines"
echo "  mcu.c     : $(grep -c agg_win_cap "$TREE/mt7996/mcu.c") lines"
echo "  debugfs.c : $(grep -c agg_win_cap "$TREE/mt7996/debugfs.c") lines"
echo "  read func : $(grep -c mt7996_agg_win_cap_read "$TREE/mt7996/debugfs.c") lines"
echo "  write func: $(grep -c mt7996_agg_win_cap_write "$TREE/mt7996/debugfs.c") lines"

echo "=== 4. Compile ==="
make -C "$SDK" package/kernel/mt76/compile V=s -j24 > /root/mt76_build_v7.log 2>&1 || true

echo "=== 5. Result ==="
KO=$TREE/mt7996/mt7996e.ko
if [ -f "$KO" ]; then
  echo "KO FOUND"
  ls -l "$KO"
  md5sum "$KO"
  echo "agg_win_cap strings: $(strings "$KO" | grep -c agg_win_cap)"
  strings "$KO" | grep agg_win_cap | head -10
else
  echo "KO MISSING — compile failed"
  echo "--- last 20 lines ---"
  tail -20 /root/mt76_build_v7.log
  echo "--- errors ---"
  grep -E 'error:|undefined' /root/mt76_build_v7.log | head -15
fi
