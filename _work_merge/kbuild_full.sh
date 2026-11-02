#!/bin/bash
# Build a full OpenWrt-patched linux-6.6.73 tree from pristine + OpenWrt patches,
# then compile Image + dtbs with the SDK toolchain.  Full speed: -j24.
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BR=/root/src/openwrt-24.10.0
KD=/root/kbuild/linux-6.6.73
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
export PATH=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$SDK/staging_dir/host/bin:$PATH

cd $KD || exit 1
echo "=== stage 1: overlay OpenWrt files/ dirs ==="
cp -a $BR/target/linux/generic/files/. $KD/
cp -a $BR/target/linux/mediatek/files/. $KD/
cp -a $BR/target/linux/mediatek/files-6.6/. $KD/
echo "files overlay done"

apply_dir() {
  local name="$1" dir="$2" ok=0 fail=0
  echo "=== stage: $name ($(ls $dir/*.patch 2>/dev/null | wc -l) patches) ==="
  for p in $(ls $dir/*.patch 2>/dev/null | sort); do
    if patch -f -p1 -d "$KD" < "$p" > /tmp/patch_last.log 2>&1; then
      ok=$((ok+1))
    else
      fail=$((fail+1))
      echo "PATCH-FAIL: $p"
      head -5 /tmp/patch_last.log
    fi
  done
  echo "$name: ok=$ok fail=$fail"
}

apply_dir "generic-backport" $BR/target/linux/generic/backport-6.6
apply_dir "generic-pending"  $BR/target/linux/generic/pending-6.6
apply_dir "generic-hack"     $BR/target/linux/generic/hack-6.6
apply_dir "platform-mediatek" $BR/target/linux/mediatek/patches-6.6

echo "=== rejects ==="
find $KD -name '*.rej' 2>/dev/null | head -20
echo "reject count: $(find $KD -name '*.rej' 2>/dev/null | wc -l)"
find $KD -name '*.orig' -delete 2>/dev/null

echo "=== stage: config ==="
cp $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config $KD/.config
$KD/scripts/config --file $KD/.config \
  -e TRACING -e TRACEPOINTS -e EVENT_TRACING -e RING_BUFFER \
  -e FTRACE -e FUNCTION_TRACER -e DYNAMIC_FTRACE -e ENABLE_DEFAULT_TRACERS \
  -e FTRACE_SYSCALLS -e KPROBES -e KPROBE_EVENTS -e DEBUG_FS

echo "=== stage: olddefconfig ==="
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC olddefconfig > /root/kbuild_olddefconfig.log 2>&1
echo "olddefconfig rc=$?"
grep -E "^CONFIG_(TRACING|TRACEPOINTS|EVENT_TRACING|FTRACE|FUNCTION_TRACER|DYNAMIC_FTRACE|ENABLE_DEFAULT_TRACERS|RING_BUFFER|KPROBES|KPROBE_EVENTS|DEBUG_FS)=" $KD/.config

echo "=== stage: build Image dtbs -j24 ==="
date
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC Image dtbs -j24 > /root/kbuild_image.log 2>&1
echo "KERNEL_BUILD_RC=$?"
date
ls -la $KD/arch/arm64/boot/Image 2>&1
ls -la $KD/arch/arm64/boot/dts/mediatek/mt7988a-bananapi-bpi-r4-poe.dtb 2>&1
echo KERNEL_DONE
