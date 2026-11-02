SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== SDK mac80211 patches (subsys) ==="
ls -la $SDK/package/kernel/mac80211/patches/subsys/ 2>&1 | tail -20
echo "=== 354 / wdrr present? ==="
ls -la $SDK/package/kernel/mac80211/patches/subsys/*dscp* $SDK/package/kernel/mac80211/patches/subsys/*wdrr* 2>&1
echo "=== SDK kernel stamps ==="
ls -la $KD/.configured $KD/.prepared $KD/.built $KD/.config 2>&1
echo "=== include/config contents ==="
ls -la $KD/include/config/ 2>&1 | head
echo "=== include/generated ==="
ls $KD/include/generated/ 2>&1 | head -20
echo "=== Module.symvers size ==="
ls -la $KD/Module.symvers 2>&1
echo "=== mac80211 build dir state ==="
ls -la $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/ 2>&1
echo "=== does build dir have our edits? ==="
grep -c "fq_weight" $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/net/mac80211/tx.c 2>&1
grep -c "wifi_dscp" $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/net/mac80211/trace.h 2>&1
echo DONE