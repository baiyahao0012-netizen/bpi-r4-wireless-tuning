SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== ipkg ko files ==="
find $BP/ipkg-aarch64_cortex-a53 -name "*.ko" -newermt "2026-11-02 18:00" 2>/dev/null | head -20
echo "=== all ipkg ko count ==="
find $BP/ipkg-aarch64_cortex-a53 -name "*.ko" 2>/dev/null | wc -l
echo "=== net/mac80211 dir ko ==="
ls -la $BP/net/mac80211/*.ko 2>&1 | head
echo "=== build log tail ==="
tail -5 /root/mac80211_build.log
echo "=== BUILD_RC ==="
grep BUILD_RC= /root/mac80211_build.log || echo NONE
echo DONE