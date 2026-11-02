#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== mt76 build dirs ==="
ls -d $SDK/build_dir/target-aarch64_cortex-a53_musl/mt76-* 2>/dev/null
echo "=== verify 355 applied in mt7996/mac.c ==="
for d in $SDK/build_dir/target-aarch64_cortex-a53_musl/mt76-*/; do
  f="$d/mt7996/mac.c"
  [ -f "$f" ] && echo "--- $f ---" && grep -n -A3 "status.rates\[0\].idx = 0" "$f" | head -8 && grep -n "MT_TXS5_F0_TX_COUNT" "$f" | head -3
done
echo "=== verify 354 applied in mac80211 trace.h ==="
for d in $SDK/build_dir/target-aarch64_cortex-a53_musl/backports-*/; do
  f="$d/net/mac80211/trace.h"
  [ -f "$f" ] && echo "--- $f ---" && grep -n -B2 -A20 "wifi_dscp" "$f" | head -50
done
echo DONE
