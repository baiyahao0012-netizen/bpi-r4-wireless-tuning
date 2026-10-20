#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== grep func names ==="
grep -n 'mt7996_agg_win_cap_read\|mt7996_agg_win_cap_write\|fops_agg_win_cap' "$TREE/mt7996/debugfs.c"
echo ""
echo "=== sed around fops block (lines 960-1095) ==="
sed -n '960,1095p' "$TREE/mt7996/debugfs.c" | cat -n
echo ""
echo "=== compile log: debugfs.o ==="
grep -i 'debugfs\.\|mt7996.*debugfs' /root/mt76_build_v7.log | tail -10
