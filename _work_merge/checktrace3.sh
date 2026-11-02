SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
echo "=== build log: trace.o compiled? ==="
grep -c "mac80211/trace.o" /root/mac80211_build.log
grep -n "mac80211/trace" /root/mac80211_build.log | head -5
echo "=== build log: any tracepoint mentions ==="
grep -n "TRACING" /root/mac80211_build.log | head -5
echo "=== lowercase wifi_dscp in ko ==="
strings -a "$KO" | grep -c "wifi_dscp"
strings -a "$KO" | grep "wifi_dscp" | head -10
echo "=== __tracepoint strings ==="
strings -a "$KO" | grep -c "__tracepoint"
strings -a "$KO" | grep "__tracepoint" | head -5
echo "=== tracepoint sections ==="
readelf -SW "$KO" 2>/dev/null | grep -iE "tracepoint|BTF" | head -10
echo "=== compare with board WDRR module ==="
strings -a "/mnt/d/Desktop/AI 辅助对话/_work_final/modules/mac80211.wdrr.ko" | grep -c "__tracepoint"
echo DONE