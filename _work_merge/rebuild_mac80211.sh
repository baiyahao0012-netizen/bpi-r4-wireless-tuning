#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
NEW=/root/kbuild/linux-6.6.73
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH

echo "=== sync new kernel config into SDK kernel build dir ==="
cp $NEW/.config $KD/.config
cp -a $NEW/include/config/. $KD/include/config/
cp -a $NEW/include/generated/. $KD/include/generated/
echo "autoconf TRACEPOINTS: $(grep -c 'CONFIG_TRACEPOINTS' $KD/include/generated/autoconf.h)"
echo "marker TRACEPOINTS: $(ls $KD/include/config/TRACEPOINTS 2>&1)"
echo "marker FTRACE: $(ls $KD/include/config/FTRACE 2>&1)"
echo "auto.conf TRACEPOINTS: $(grep -c 'CONFIG_TRACEPOINTS' $KD/include/config/auto.conf)"

echo "=== clean mac80211 ==="
cd $SDK
make package/kernel/mac80211/clean V=s -j24 > /root/mac80211_clean.log 2>&1
echo "clean rc=$?"

echo "=== compile mac80211 -j24 ==="
date
make package/kernel/mac80211/compile V=s -j24 > /root/mac80211_build2.log 2>&1
echo "compile rc=$?"
date
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/.pkgdir/kmod-mac80211/lib/modules/6.6.73/mac80211.ko
ls -la $KO 2>&1
echo "=== tracepoints in new ko ==="
strings -a $KO 2>/dev/null | grep -c "__tracepoint"
readelf -SW $KO 2>/dev/null | grep -ciE "tracepoint"
echo MAC80211_DONE
