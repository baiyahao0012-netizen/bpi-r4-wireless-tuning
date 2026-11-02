SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
MT=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== search MT_TXS5_F0_TX_COUNT whole mt76 tree ==="
grep -rn "MT_TXS5_F0" $MT/ 2>/dev/null | head -10
echo "=== MT_TXS5 defs ==="
grep -rn "MT_TXS5" $MT/mt7996/mac.h 2>/dev/null | head -20
echo "=== mt76 mac.h TXS5 lines ==="
grep -rn "TXS5" $MT/mt76.h $MT/mt76/mac80211.c 2>/dev/null | head -10
echo "=== their mt76? do we have their mt76 source? ==="
ls /root/merge/incoming/bsdx/backports-src/ 2>/dev/null
echo DONE