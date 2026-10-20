#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== mac80211 backports config ==="
grep MAC80211_DEBUGFS "$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.config" 2>/dev/null || echo "NOT FOUND"
echo ""
echo "=== kernel 6.6.73 config for reference ==="
grep MAC80211 "$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config" 2>/dev/null | head -20
echo ""
echo "=== mt76 Makefile Kconfig ==="
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
grep -r MAC80211_DEBUGFS "$TREE/" 2>/dev/null | head -10
echo ""
echo "=== mt7996 debugfs.c full #ifdef check around fops insertion ==="
# show line numbers of ALL lines that mention CONFIG_ or #if
awk 'NR>=920 && NR<=1090 && /#(ifdef|ifndef|if|endif|else|elif|define)/ { print NR": "$0 }' "$TREE/mt7996/debugfs.c"
