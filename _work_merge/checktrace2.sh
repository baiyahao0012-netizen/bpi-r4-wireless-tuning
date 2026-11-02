SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== BP top ==="
ls -la $BP 2>&1 | head -30
echo "=== net/mac80211 dir ==="
ls -la $BP/net/mac80211/ 2>&1 | head -15
echo "=== find .config under BP ==="
find $BP -maxdepth 1 -name ".*" 2>/dev/null | head -20
echo "=== find any mac80211.ko unstripped ==="
find $SDK/build_dir -name "mac80211.ko" 2>/dev/null
echo "=== grep tracing in build logs ==="
grep -c "MAC80211_TRACING" /root/mac80211_build.log
grep -n "MAC80211_TRACING" /root/mac80211_build.log | head -5
echo "=== ipk contents ==="
cd /tmp && rm -rf ipkx && mkdir ipkx && cd ipkx && tar -xzf $SDK/bin/targets/mediatek/filogic/packages/kmod-mac80211_6.6.73.6.12.6-r1_aarch64_cortex-a53.ipk 2>&1 | head -3; ls -la; tar -xzf data.tar.gz 2>&1 | head -3; find . -name "*.ko" -exec ls -la {} \;
echo DONE