#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
export PATH=$SDK/staging_dir/host/bin:$PATH

echo "=== backup config ==="
cp -n $KD/.config $KD/.config.before-ftrace || true

echo "=== enable ftrace options ==="
$KD/scripts/config --file $KD/.config \
  -e TRACING -e TRACEPOINTS -e EVENT_TRACING -e RING_BUFFER \
  -e FTRACE -e FUNCTION_TRACER -e DYNAMIC_FTRACE -e ENABLE_DEFAULT_TRACERS \
  -e FTRACE_SYSCALLS -e KPROBES -e KPROBE_EVENTS -e DEBUG_FS

echo "=== olddefconfig ==="
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC olddefconfig > /root/kernel_olddefconfig.log 2>&1
echo "olddefconfig rc=$?"

echo "=== resulting key options ==="
grep -E "^CONFIG_(TRACING|TRACEPOINTS|EVENT_TRACING|FTRACE|FUNCTION_TRACER|DYNAMIC_FTRACE|ENABLE_DEFAULT_TRACERS|RING_BUFFER|KPROBES|KPROBE_EVENTS|DEBUG_FS)=" $KD/.config || true
echo "--- unset ones ---"
grep -E "^# CONFIG_(TRACING|TRACEPOINTS|EVENT_TRACING|FTRACE|FUNCTION_TRACER|DYNAMIC_FTRACE|ENABLE_DEFAULT_TRACERS)" $KD/.config || true

echo "=== vermagic-relevant options ==="
grep -E "^CONFIG_(MODVERSIONS|MODULE_SIG|LOCALVERSION|SMP|ARM64)=" $KD/.config || true

echo "=== build Image + dtbs ==="
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC Image dtbs -j16 > /root/kernel_build.log 2>&1
echo "KERNEL_BUILD_RC=$?"
ls -la $KD/arch/arm64/boot/Image 2>&1 || true
ls $KD/arch/arm64/boot/dts/mediatek/mt7988a-bananapi-bpi-r4-poe.dtb 2>&1 || true
echo KERNEL_DONE
