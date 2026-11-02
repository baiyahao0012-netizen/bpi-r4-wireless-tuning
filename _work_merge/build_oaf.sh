#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
SRC=$SDK/package/OpenAppFilter/oaf/src
rm -rf /root/oafbuild; mkdir -p /root/oafbuild
cp $SRC/* /root/oafbuild/
cd /root/oafbuild
KCF='-Wno-error=missing-prototypes -Wno-error=missing-declarations -Wno-error=unused-variable -Wno-error=declaration-after-statement -Wno-error=implicit-fallthrough -Wno-error=missing-braces -Wno-error=parentheses -Wno-error=format -Wno-frame-larger-than'
make -C $KD M=/root/oafbuild ARCH=arm64 CROSS_COMPILE=$TC KCFLAGS="$KCF" modules -j16 2>&1 | tail -25
echo "=== built ==="
ls -la /root/oafbuild/oaf.ko 2>&1
RD=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
$RD -SW /root/oafbuild/oaf.ko 2>/dev/null | grep -i this_module
md5sum /root/oafbuild/oaf.ko
echo "=== modinfo ==="
$RD -p .modinfo /root/oafbuild/oaf.ko 2>/dev/null | head -10
echo OAFBUILD_DONE
