#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== mt7996_mcu_sta_ba full (1100-1160) ==="
sed -n '1100,1160p' "$TREE/mt7996/mcu.c"
echo ""
echo "=== struct mt7996_sta definition ==="
grep -n -A30 '^struct mt7996_sta {' "$TREE/mt7996/mt7996.h"
echo ""
echo "=== txwi_free caller function (mac.c 1020-1085) ==="
sed -n '1020,1085p' "$TREE/mt7996/mac.c"
