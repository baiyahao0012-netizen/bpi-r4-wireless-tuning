SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PKG=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
IPK=/tmp/ipkx/d/lib/modules/6.6.73/mac80211.ko
BOARD="/mnt/d/Desktop/AI 辅助对话/_work_final/modules/mac80211.wdrr.ko"
for f in "$PKG" "$IPK" "$BOARD"; do
  echo "=== $f ==="
  ls -la "$f" 2>&1
  file "$f" 2>&1
  echo -n "format-string: "; grep -ac "dir=%u stage=%u dscp=0x%02x" "$f" 2>/dev/null || echo 0
  echo -n "wifi_dscp: "; grep -ac "wifi_dscp" "$f" 2>/dev/null || echo 0
  echo -n "fq_weight: "; grep -ac "fq_weight" "$f" 2>/dev/null || echo 0
  echo -n "section headers: "; readelf -h "$f" 2>/dev/null | grep -c "Number of section headers" || echo "none"
  echo -n "tracepoint sections: "; readelf -SW "$f" 2>/dev/null | grep -c -i tracepoint
done
echo "=== readelf -SW on PKG (first 25) ==="
readelf -SW "$PKG" 2>&1 | head -25
echo DONE