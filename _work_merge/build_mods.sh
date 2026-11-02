#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
KD=/root/kbuild/linux-6.6.73
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH
export STAGING_DIR=$SDK/staging_dir
cd $KD
date
make ARCH=arm64 CROSS_COMPILE=$TC modules -j24 > /root/kmods_build.log 2>&1
echo "make modules rc=$?"
date
echo "=== ko count ==="
find $KD -name "*.ko" -not -path "*/.tmp_versions/*" | wc -l
echo "=== errors ==="
grep -c "Error\|error:" /root/kmods_build.log
echo MODULES_BUILD_DONE
