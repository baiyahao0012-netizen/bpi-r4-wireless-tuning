#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=/root/kbuild/linux-6.6.73
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
echo "=== tools ==="
which bison flex gcc make
bison --version | head -1
flex --version
echo "=== olddefconfig ==="
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC olddefconfig > /root/kbuild_olddefconfig.log 2>&1
echo "olddefconfig rc=$?"
grep -E "^CONFIG_(TRACING|TRACEPOINTS|EVENT_TRACING|FTRACE|FUNCTION_TRACER|DYNAMIC_FTRACE|ENABLE_DEFAULT_TRACERS|RING_BUFFER)=" $KD/.config
echo "=== build Image dtbs -j24 ==="
date
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC Image dtbs -j24 > /root/kbuild_image.log 2>&1
echo "KERNEL_BUILD_RC=$?"
date
ls -la $KD/arch/arm64/boot/Image 2>&1
ls -la $KD/arch/arm64/boot/dts/mediatek/mt7988a-bananapi-bpi-r4-poe.dtb 2>&1
echo KERNEL_DONE
