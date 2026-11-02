#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH
cd $SDK
echo "=== mac80211 clean ==="
make package/kernel/mac80211/clean V=s > /root/mac_clean2.log 2>&1
echo "clean rc=$?"
echo "=== mac80211 compile ==="
make package/kernel/mac80211/compile V=s -j24 > /root/mac_pkg2.log 2>&1
echo "compile rc=$?"
RD=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic
echo "=== this_module sizes (want 0x480) ==="
for n in compat cfg80211 mac80211; do
  f=$(find $BD/mac80211-regular -path "*.pkgdir*" -name "$n.ko" 2>/dev/null | head -1)
  if [ -n "$f" ]; then echo "$n.ko: $($RD -SW $f 2>/dev/null | grep -o 'this_module.*' | head -1)"; else echo "$n.ko MISSING"; fi
done
echo MAC2_DONE
