#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== debugfs.c #ifdef structure ==="
grep -n '#ifdef\|#ifndef\|#endif\|#if ' "$TREE/mt7996/debugfs.c"
echo ""
echo "=== fops block context (980-1065) ==="
sed -n '980,1065p' "$TREE/mt7996/debugfs.c" | cat -n
echo ""
echo "=== check: fops_agg_win_cap .read points to what? ==="
KO=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt7996/mt7996e.ko
objdump -r "$KO" 2>/dev/null | grep -B5 -A5 'fops_agg_win_cap' | head -30
