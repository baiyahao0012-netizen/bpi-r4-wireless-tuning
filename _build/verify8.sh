#!/bin/bash
exec > /root/verify8.log 2>&1
B=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "=== apply log tail ==="
grep -E "ALL_APPLIED|FAIL|OK " /root/build8.log | head -10
echo "=== source changes ==="
grep -c "flow->quantum ? flow->quantum" "$B/include/net/fq_impl.h"
grep -c "int quantum;" "$B/include/net/fq.h"
grep -c "fq_weight\[IEEE80211_NUM_ACS\]" "$B/net/mac80211/tx.c"
grep -c "ieee80211_wdrr_mark_loaded" "$B/net/mac80211/tx.c"
echo "=== all ko files ==="
find /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir -name "mac80211.ko" 2>/dev/null
echo "=== ko symbols check ==="
KO=$(find /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir -name "mac80211.ko" 2>/dev/null | head -1)
echo "KO=$KO"
if [ -n "$KO" ]; then
  /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-nm "$KO" 2>/dev/null | grep -i "fq_weight" | head -5
  strings "$KO" 2>/dev/null | grep -i "fq_weight" | head -3
  strings "$KO" 2>/dev/null | grep -i "WDRR" | head -3
  ls -la "$KO"
fi
echo VERIFY8_DONE
