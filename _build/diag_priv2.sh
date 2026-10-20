#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== all file_operations (non-seq) fops in mt7996 ==="
grep -n 'static const struct file_operations' "$TREE/mt7996/debugfs.c"
echo ""
echo "=== each: how does its read/write access private_data? ==="
for fname in fops_rf_regval fops_fixed_rate fops_sys_recovery_ops fops_agg_win_cap; do
  echo "--- $fname ---"
  # find the fops block
  LINE=$(grep -n "static const struct file_operations $fname" "$TREE/mt7996/debugfs.c" | head -1 | cut -d: -f1)
  if [ -n "$LINE" ]; then
    sed -n "${LINE},$((LINE+10))p" "$TREE/mt7996/debugfs.c"
  fi
  # find the read/write functions
  grep -n -B1 -A10 "\.read\|\.write" "$TREE/mt7996/debugfs.c" | grep -A15 "^\s*\.read\|^\s*\.write" | head -40
done
echo ""
echo "=== fops_rf_regval: its write func (uses file->private_data?) ==="
grep -n -A20 'mt7996_rf_regval_set\b' "$TREE/mt7996/debugfs.c" | head -25
grep -n -A20 'mt7996_rf_regval_get\b' "$TREE/mt7996/debugfs.c" | head -25
