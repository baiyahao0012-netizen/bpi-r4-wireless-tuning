#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== main.c mt7996_ampdu_action (937-995) ==="
sed -n '937,995p' "$TREE/mt7996/main.c"
echo ""
echo "=== mac.c around 1076 (BA restart mechanism) ==="
sed -n '1050,1090p' "$TREE/mt7996/mac.c"
