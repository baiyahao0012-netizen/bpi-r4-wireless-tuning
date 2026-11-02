#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=/root/kbuild/linux-6.6.73
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
export PATH=$SDK/staging_dir/host/bin:$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin:$PATH

cd $KD
echo "=== save full-ftrace config + Image ==="
cp .config /root/config.full-ftrace
cp arch/arm64/boot/Image /root/Image.full-ftrace 2>/dev/null
ls -la /root/Image.full-ftrace

echo "=== strip heavy tracers, keep minimal ==="
scripts/config --file .config \
  -d FTRACE_SYSCALLS -d FUNCTION_GRAPH_TRACER -d FUNCTION_TRACER -d DYNAMIC_FTRACE \
  -d KPROBES -d KPROBE_EVENTS -d UPROBE_EVENTS -d ENABLE_DEFAULT_TRACERS \
  -d HIST_TRIGGERS -d TRACE_EVENT_INJECT -d TRACER_SNAPSHOT -d BLK_DEV_IO_TRACE \
  -d STACK_TRACER -d IRQSOFF_TRACER -d PREEMPT_TRACER -d SCHED_TRACER \
  -d HWLAT_TRACER -d OSNOISE_TRACER -d TIMERLAT_TRACER -d MMIOTRACE \
  -d BOOTTIME_TRACING -d DYNAMIC_EVENTS -d BPF_EVENTS -d USER_EVENTS \
  -d FPROBE_EVENTS -d KPROBE_EVENTS -d KPROBES \
  -e SYNTH_EVENTS -e TRACING -e FTRACE -e TRACEPOINTS -e EVENT_TRACING -e RING_BUFFER

echo "=== olddefconfig ==="
make ARCH=arm64 CROSS_COMPILE=$TC olddefconfig > /root/mincfg.log 2>&1
echo "rc=$?"
echo "=== resulting tracing options ==="
grep -E "^CONFIG_(TRACING|TRACEPOINTS|EVENT_TRACING|RING_BUFFER|FTRACE|FUNCTION_TRACER|DYNAMIC_FTRACE|FTRACE_SYSCALLS|KPROBES|KPROBE_EVENTS|GENERIC_TRACER|NOP_TRACER|SYNTH_EVENTS|DYNAMIC_EVENTS|TRACE_CLOCK|BINARY_PRINTF)=" .config | sort

echo "=== build -j24 ==="
date
make ARCH=arm64 CROSS_COMPILE=$TC Image dtbs -j24 > /root/kbuild_min.log 2>&1
echo "build rc=$?"
date
ls -la arch/arm64/boot/Image
echo "=== compressed sizes ==="
echo -n "gzip -9: "; gzip -9 -c arch/arm64/boot/Image | wc -c
echo -n "zstd -19: "; zstd -19 -c arch/arm64/boot/Image 2>/dev/null | wc -c
echo -n "lzma -9: "; xz --format=lzma -9 -c arch/arm64/boot/Image 2>/dev/null | wc -c
echo "old kernel gzip = 5633434"
echo MIN_KERNEL_DONE
