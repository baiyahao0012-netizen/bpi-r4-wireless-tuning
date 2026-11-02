SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
MT=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== mt76 patches dir ==="
ls -la $SDK/package/kernel/mt76/patches/ 2>&1 | head -20
echo "=== mt76 tree exists? ==="
ls -d $MT 2>&1
echo "=== target line in our mt76 ==="
grep -n "info->status.rates\[0\].idx = -1" $MT/mt7996/mac.c 2>&1
echo "=== context ==="
grep -n -B8 -A4 "info->status.rates\[0\].idx = -1" $MT/mt7996/mac.c 2>&1 | head -30
echo "=== does mt7996_mac_add_txs_skb exist ==="
grep -n "mt7996_mac_add_txs_skb" $MT/mt7996/mac.c 2>&1 | head
echo "=== MT_TXS5_F0_TX_COUNT defined? ==="
grep -rn "MT_TXS5_F0_TX_COUNT" $MT/mt7996/ 2>&1 | head -5
echo "=== our mt76 mods present? (agg_win_cap etc) ==="
grep -c "agg_win_cap" $MT/mt7996/debugfs.c 2>/dev/null
grep -c "agg_win_cap" $MT/mt7996/mt7996.h 2>/dev/null
echo "=== current mt7996e.ko in tree ==="
ls -la $MT/mt7996/mt7996e.ko 2>&1
echo DONE