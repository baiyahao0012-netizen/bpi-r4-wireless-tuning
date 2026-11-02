for i in $(seq 1 50); do
  if grep -q "BUILD_RC=" /root/mac80211_build.log 2>/dev/null; then break; fi
  sleep 5
done
grep BUILD_RC= /root/mac80211_build.log || echo STILL_RUNNING
echo "=== errors ==="
grep -nE "^make.*Error|error:" /root/mac80211_build.log | grep -v ignored | head -10
echo "=== ko artifacts ==="
find /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular -name "mac80211.ko" 2>/dev/null
echo "=== ipk artifacts ==="
find /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/bin -name "kmod-mac80211*.ipk" -o -name "kmod-cfg80211*.ipk" 2>/dev/null | head
echo DONE