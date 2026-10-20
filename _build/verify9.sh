#!/bin/bash
exec > /root/verify9.log 2>&1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== regular source tree exists? ==="
ls -d "$B" 2>&1
echo "=== source changes in regular ==="
grep -c "flow->quantum ? flow->quantum" "$B/include/net/fq_impl.h" 2>/dev/null
grep -c "int quantum;" "$B/include/net/fq.h" 2>/dev/null
grep -c "fq_weight\[IEEE80211_NUM_ACS\]" "$B/net/mac80211/tx.c" 2>/dev/null
grep -c "ieee80211_wdrr_mark_loaded" "$B/net/mac80211/tx.c" 2>/dev/null
echo "=== ko symbols ==="
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
ls -la "$KO"
$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-nm "$KO" 2>/dev/null | grep -i "fq_weight" | head -6
echo "--- strings ---"
strings "$KO" | grep -i "WDRR" | head -3
strings "$KO" | grep -i "per-AC weight" | head -2
echo "=== vermagic ==="
$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-modinfo "$KO" 2>/dev/null | grep -E "vermagic|depends|parm" | head -8
echo VERIFY9_DONE
