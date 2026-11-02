#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== SDK KD autoconf ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_DYNAMIC_FTRACE|CONFIG_TRACEPOINTS|CONFIG_FTRACE=|CONFIG_KPROBES" $KD/include/generated/autoconf.h 2>/dev/null | head
echo "=== SDK KD .config ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_DYNAMIC_FTRACE|CONFIG_TRACEPOINTS|CONFIG_FTRACE=" $KD/.config 2>/dev/null | head
echo "=== kbuild tree autoconf ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_DYNAMIC_FTRACE|CONFIG_TRACEPOINTS|CONFIG_FTRACE=" /root/kbuild/linux-6.6.73/include/generated/autoconf.h 2>/dev/null | head
echo "=== kbuild tree .config ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_DYNAMIC_FTRACE|CONFIG_TRACEPOINTS|CONFIG_FTRACE=" /root/kbuild/linux-6.6.73/.config 2>/dev/null | head
echo DONE
