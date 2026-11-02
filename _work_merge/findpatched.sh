#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== SDK build_dir ==="
ls $SDK/build_dir/target-aarch64_cortex-a53_musl/ 2>/dev/null | head -20
echo "=== find mac.c / trace.h with wifi_dscp ==="
find $SDK/build_dir -name "mac.c" -path "*mt7996*" 2>/dev/null | head -5
find $SDK/build_dir -name "trace.h" -path "*mac80211*" 2>/dev/null | head -5
echo "=== grep wifi_dscp anywhere in SDK build_dir ==="
grep -rl "wifi_dscp" $SDK/build_dir 2>/dev/null | head -10
echo "=== grep MT_TXS5_F0_TX_COUNT with rates[0].count ==="
grep -rln "status.rates\[0\].count" $SDK/build_dir 2>/dev/null | head -5
echo DONE
