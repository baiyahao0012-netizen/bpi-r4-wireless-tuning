#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== debugfs.c #ifdef / #endif with line numbers ==="
awk '/^#(ifdef|ifndef|if|endif|else)/ { print NR": "$0 }' "$TREE/mt7996/debugfs.c"
echo ""
echo "=== check CONFIG_MAC80211_DEBUGFS in kernel config ==="
find /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64 -name ".config" 2>/dev/null | head -3 | while read f; do echo "--- $f ---"; grep MAC80211_DEBUGFS "$f" || echo "(no MAC80211_DEBUGFS)"; done
echo ""
echo "=== check mt76-2025.01.14~8e4f72b6.tar.zst CONFIG ==="
zstdcat /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/dl/mt76-2025.01.14~8e4f72b6.tar.zst 2>/dev/null | tar -tf - 2>/dev/null | head -3
