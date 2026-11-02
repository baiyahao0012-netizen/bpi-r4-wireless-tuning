#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic
M=$BD/mt76-2025.01.14~8e4f72b6
echo "=== 355: mt7996/mac.c ==="
grep -n -B3 -A6 "status.rates\[0\].idx = 0" $M/mt7996/mac.c | head -20
echo "=== 355 marker: MT_TXS5_F0_TX_COUNT in mt7996/mac.c ==="
grep -n "MT_TXS5_F0_TX_COUNT" $M/mt7996/mac.c | head -5
echo "=== A+ / txwi_rate markers in tx.c ==="
grep -n "status.rates\[0\].count" $M/tx.c | head -5
echo "=== 354: mac80211 trace.h ==="
B=$BD/mac80211-regular/backports-6.12.6
ls -d $B 2>/dev/null && grep -n "wifi_dscp" $B/net/mac80211/trace.h | head -10
echo "=== 354: trace.c ==="
grep -n "wifi_dscp" $B/net/mac80211/trace.c 2>/dev/null | head -5
echo "=== deployed mac80211.ko md5 vs SDK pkgdir ==="
md5sum $BD/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko /root/bpstage/mac80211.ko 2>/dev/null
echo DONE
