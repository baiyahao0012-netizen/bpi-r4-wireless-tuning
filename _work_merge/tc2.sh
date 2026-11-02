SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== toolchain bin prefixes ==="
ls $SDK/staging_dir/toolchain-*/bin/ 2>/dev/null | grep -E "gcc$|gcc-13" | head
echo "=== TARGET_CROSS from .config ==="
grep -n "CONFIG_TARGET_NAME\|CONFIG_ARCH\|CONFIG_TARGET_ARCH" $SDK/.config | head
echo "=== kernel tree: already built? ==="
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
ls -la $KD/include/generated/autoconf.h $KD/include/config/auto.conf 2>&1
ls -la $KD/Module.symvers $KD/vmlinux 2>&1
echo "=== current FTRACE-ish options ==="
grep -nE "^CONFIG_(FTRACE|TRACEPOINTS|TRACING|EVENT_TRACING|FUNCTION_TRACER|DYNAMIC_FTRACE|ENABLE_DEFAULT_TRACERS|RING_BUFFER|TRACEFS)" $KD/.config | head -20
echo "=== LOCALVERSION / version ==="
grep -nE "^CONFIG_LOCALVERSION|^CONFIG_MODVERSIONS|^CONFIG_MODULE_SIG" $KD/.config | head
echo DONE