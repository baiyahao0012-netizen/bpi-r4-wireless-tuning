#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH
rm -rf /root/gbh; mkdir -p /root/gbh
cp /root/src/openwrt-24.10.0/package/kernel/gpio-button-hotplug/src/* /root/gbh/
echo "--- src files ---"
ls /root/gbh/
cd /root/kbuild/linux-6.6.73
make ARCH=arm64 CROSS_COMPILE=$TC M=/root/gbh modules -j8 > /root/gbh_build.log 2>&1
echo "rc=$?"
tail -12 /root/gbh_build.log
ls -la /root/gbh/*.ko 2>&1
if [ -f /root/gbh/gpio-button-hotplug.ko ]; then
  cp /root/gbh/gpio-button-hotplug.ko /root/modstage/lib/modules/6.6.73/
  echo "copied; total now: $(ls /root/modstage/lib/modules/6.6.73/*.ko | wc -l)"
fi
echo GBH_DONE
