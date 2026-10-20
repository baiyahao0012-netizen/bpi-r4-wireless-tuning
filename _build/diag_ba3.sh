#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== mt7996_mcu_add_tx_ba full (1160-1230) ==="
sed -n '1160,1235p' "$TREE/mt7996/mcu.c"
