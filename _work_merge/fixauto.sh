#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH
echo "=== try syncconfig in SDK KD ==="
make -C $KD ARCH=arm64 CROSS_COMPILE=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl- olddefconfig > /root/syncconfig.log 2>&1
echo "rc=$?"
tail -8 /root/syncconfig.log
echo "=== after ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_DYNAMIC_FTRACE|CONFIG_KPROBES|CONFIG_TRACEPOINTS" $KD/include/generated/autoconf.h 2>/dev/null | head
echo "=== auto.conf ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_KPROBES" $KD/include/config/auto.conf 2>/dev/null | head
echo DONE
