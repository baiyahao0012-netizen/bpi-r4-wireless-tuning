#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== backport/autoconf.h in mt76 tree ==="
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
grep -r MAC80211_DEBUGFS "$TREE/backport/" 2>/dev/null | head -10 || echo "not in mt76/backport"
echo ""
echo "=== find all autoconf.h ==="
find /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64 -name autoconf.h 2>/dev/null | while read f; do echo "--- $f ---"; grep MAC80211_DEBUGFS "$f" || echo "(no MAC80211_DEBUGFS)"; done
echo ""
echo "=== manually define MAC80211_DEBUGFS and see if it fixes ==="
# just test: grep the preprocessed output
mkdir -p /tmp/pp_test
cd /tmp/pp_test
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
LINUX=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
# Use the actual gcc command from .cmd but add -DCONFIG_MAC80211_DEBUGFS=y and -E (preprocess only)
aarch64-openwrt-linux-musl-gcc -E -DCONFIG_MAC80211_DEBUGFS=y -include backport/autoconf.h -include backport/backport.h -I"$TREE" -DCONFIG_MAC80211_MESH -DCONFIG_MT798X_WMAC -I"$LINUX/include" -I"$LINUX/arch/arm64/include" -include "$LINUX/include/linux/kconfig.h" "$TREE/mt7996/debugfs.c" 2>/dev/null | grep -E 'mt7996_agg_win_cap_read|mt7996_agg_win_cap_write|fops_agg_win_cap = \{' | head -10 || echo "(preprocess failed or no matches)"
