#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== mt7996_init_debugfs full body (lines 920-1020) ==="
sed -n '920,1020p' "$TREE/mt7996/debugfs.c" | cat -n
echo ""
echo "=== debugfs_create_file calls around agg_win_cap ==="
grep -n -B1 -A1 'debugfs_create_file.*agg_win_cap' "$TREE/mt7996/debugfs.c"
echo ""
echo "=== compare: how tx_stats fops gets dev ==="
grep -n -B1 -A3 'mt7996_tx_stats' "$TREE/mt7996/debugfs.c" | head -20
