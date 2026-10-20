#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== include/config/MAC80211_DEBUGFS ==="
ls -la "$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/include/config/"*MAC80211* 2>/dev/null || echo "NOT in mt76 tree include/config"
ls -la "$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/include/config/"*MAC80211* 2>/dev/null | head -10 || echo "NOT in linux-6.6.73 include/config"
echo ""
echo "=== mt76 .cmd shows expected dep ==="
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
cat "$TREE/mt7996/.debugfs.o.cmd" 2>/dev/null | head -3 || echo "no cmd file"
echo ""
echo "=== compile debugfs.c with preprocessed output ==="
# Get the actual cc command from compile log
grep -A1 'debugfs.c' /root/mt76_build_v7.log | head -5
