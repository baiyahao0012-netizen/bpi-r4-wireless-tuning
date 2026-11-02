SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PKG=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
echo "=== all section names ==="
readelf -SW "$PKG" 2>/dev/null | awk "{print \$2}" | grep "^\." | sort | head -60
echo "=== symtab: wifi_dscp ==="
readelf -sW "$PKG" 2>/dev/null | grep -i "wifi_dscp" | head -20
echo "=== symtab: __tracepoint count ==="
readelf -sW "$PKG" 2>/dev/null | grep -c "__tracepoint"
echo "=== symtab: __tracepoint sample ==="
readelf -sW "$PKG" 2>/dev/null | grep "__tracepoint" | head -10
echo "=== symtab: drv_ tracepoints ==="
readelf -sW "$PKG" 2>/dev/null | grep -c "tracepoint_drv_"
echo "=== compare WDRR module symtab ==="
readelf -sW "/mnt/d/Desktop/AI 辅助对话/_work_final/modules/mac80211.wdrr.ko" 2>/dev/null | grep -c "__tracepoint"
echo DONE