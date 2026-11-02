SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
CFG=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-cfg80211/lib/modules/6.6.73/cfg80211.ko
echo "=== files ==="
ls -la "$KO" "$CFG" 2>&1
echo "=== md5 ==="
md5sum "$KO" "$CFG" 2>&1
echo "=== vermagic ==="
strings "$KO" 2>/dev/null | grep -m1 vermagic
echo "=== fq_weight ==="
strings "$KO" 2>/dev/null | grep -m2 fq_weight
echo "=== WDRR marker ==="
strings "$KO" 2>/dev/null | grep -m1 "private WDRR"
echo "=== wifi_dscp strings ==="
strings "$KO" 2>/dev/null | grep -m4 "wifi_dscp\|WIFI_DSCP"
echo "=== tracepoint symbols ==="
nm "$KO" 2>/dev/null | grep -i "wifi_dscp" | head -5
echo "=== ipk list ==="
ls -la $SDK/bin/targets/mediatek/filogic/packages/kmod-mac80211_*.ipk $SDK/bin/targets/mediatek/filogic/packages/kmod-cfg80211_*.ipk 2>&1
echo DONE