#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== 'Length:' printing code in debugfs.c ==="
grep -n -B2 -A12 '"Length:' "$TREE/mt7996/debugfs.c"
echo ""
echo "=== tx_stats_show_phy full (find histogram source) ==="
grep -n -A45 'mt7996_tx_stats_show_phy' "$TREE/mt7996/debugfs.c" | head -60
