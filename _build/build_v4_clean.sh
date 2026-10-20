#!/bin/bash
# build_v4_clean.sh — compile-only build of the debug-free deliverable .ko.
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PATCHDIR=$SDK/package/kernel/mt76/patches
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6

echo "=== reset ==="
rm -rf "$TREE"; rm -f "$PATCHDIR/999"*
make -C "$SDK" package/kernel/mt76/prepare V=s 2>&1 | tail -2

echo "=== apply v4_clean ==="
cp '/mnt/d/Desktop/AI 辅助对话/_build/apply_v4_clean.py' /root/apply_v4_clean.py
python3 /root/apply_v4_clean.py "$TREE"

echo "=== compile ==="
make -C "$SDK" package/kernel/mt76/compile V=s -j24 > /root/mt76_build_clean.log 2>&1 || true
KO=$TREE/mt7996/mt7996e.ko
if [ -f "$KO" ]; then
  echo "BUILD OK md5=$(md5sum "$KO"|cut -d' ' -f1)"
  echo "SIZE=$(stat -c%s "$KO")"
  echo "--- verify no debug strings ---"
  strings "$KO" | grep -c 'aggcap_dbg' || echo "aggcap_dbg count=0"
  strings "$KO" | grep -c 'agg_win_cap' || true
else
  echo "BUILD FAIL"; grep -E 'error:' /root/mt76_build_clean.log | head -20; exit 1
fi
