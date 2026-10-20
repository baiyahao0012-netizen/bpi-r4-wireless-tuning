#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== lines 810-845 ==="
sed -n '810,845p' "$TREE/mt7996/debugfs.c" | cat -n
echo ""
echo "=== lines 920-930 ==="
sed -n '920,930p' "$TREE/mt7996/debugfs.c" | cat -n
echo ""
echo "=== check CONFIG_MAC80211_DEBUGFS in linux-6.6.73/.config ==="
grep MAC80211_DEBUGFS /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config || echo "NOT DEFINED (defaults to n)"
echo ""
echo "=== check what MAC80211_DEBUGFS controls in mt76 Makefile ==="
find "$TREE" -name Makefile -exec grep -l MAC80211_DEBUGFS {} \;
