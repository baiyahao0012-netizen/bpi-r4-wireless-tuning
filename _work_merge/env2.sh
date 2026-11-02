SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== SDK build_dir linux-mediatek_filogic ==="
ls -la $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/ 2>&1 | head -20
echo "=== mac80211-regular ==="
ls -la $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/ 2>&1 | head
echo "=== backports dir ==="
ls -d $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-* 2>&1
echo "=== mac80211 pkg source in SDK? ==="
ls -la $SDK/package/kernel/ 2>&1 | head
echo "=== openwrt src tree ==="
ls /root/src/openwrt-24.10.0/ 2>&1 | head -20
ls -d /root/src/openwrt-24.10.0/package/kernel/mac80211 /root/src/openwrt-24.10.0/package/kernel/mt76 2>&1
echo "=== openwrt src .config ==="
ls -la /root/src/openwrt-24.10.0/.config 2>&1
grep -E "MAC80211_TRACING|CONFIG_TARGET_mediatek|CONFIG_TARGET_DEVICE" /root/src/openwrt-24.10.0/.config 2>/dev/null | head -20
echo "=== SDK dl ==="
ls $SDK/dl/ 2>&1 | head -30
echo "=== mt76 build dir ==="
ls -d $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-* 2>&1
echo DONE