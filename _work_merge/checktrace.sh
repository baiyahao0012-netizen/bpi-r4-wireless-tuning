SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== CPTCFG_MAC80211_TRACING in backports .config ==="
grep -n "MAC80211_TRACING\|MAC80211_MESSAGE_TRACING\|CFG80211_TRACING" $BP/.config 2>&1
echo "=== trace.o built? ==="
ls -la $BP/net/mac80211/trace.o 2>&1
echo "=== .ko symbols (readelf) ==="
readelf -sW $BP/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko 2>/dev/null | grep -ci "wifi_dscp" || echo "readelf: 0"
echo "=== section __tracepoints_strings? ==="
readelf -SW $BP/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko 2>/dev/null | grep -i "tracepoint" | head
echo "=== strings __tracepoint ==="
strings $BP/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko | grep -c "__tracepoint" 
echo "=== sample tracepoint names ==="
strings $BP/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko | grep "__tracepoint" | head -8
echo "=== MT76 tracing config? ==="
grep -n "CPTCFG_MAC80211" $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/.config 2>/dev/null | head
echo DONE