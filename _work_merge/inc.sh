T=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== mac.c includes ==="
head -20 $T/mt7996/mac.c
echo "=== bitfield.h anywhere in mt76? ==="
grep -rl "linux/bitfield.h" $T/ 2>/dev/null | head -5
echo "=== MT_TXS0_ACK_ERROR_MASK def ==="
grep -rn "define MT_TXS0_ACK_ERROR_MASK" $T/ 2>/dev/null | head -3
echo "=== MT_TXS5_F0_TX_COUNT def ==="
grep -rn "define MT_TXS5_F0_TX_COUNT" $T/ 2>/dev/null | head -3
echo "=== mt7996.h includes ==="
grep -n "#include" $T/mt7996/mt7996.h | head -20
echo "=== does mt76.h include bitfield? ==="
grep -n "include" $T/mt76.h | head -20
echo DONE