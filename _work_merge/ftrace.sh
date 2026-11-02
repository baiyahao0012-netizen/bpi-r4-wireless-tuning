SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
K=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config
echo "=== kernel .config exists? ==="
ls -la $K 2>&1
echo "=== FTRACE / TRACING options in kernel config ==="
grep -E "^CONFIG_(FTRACE|TRACEPOINTS|TRACING|FUNCTION_TRACER|DYNAMIC_FTRACE|ENABLE_DEFAULT_TRACERS|NOP_TRACER|GENERIC_TRACER|STACK_TRACER|FTRACE_SYSCALLS)" $K 2>&1 | head -20
echo "=== is CONFIG_TRACING set? ==="
grep -E "CONFIG_TRACING" $K 2>&1 | head
echo "=== Makefile: how CPTCFG_* are derived ==="
grep -n "config-" $SDK/package/kernel/mac80211/Makefile | head -40
echo "=== search MAC80211_TRACING in all pkg makefiles ==="
grep -rn "MAC80211_TRACING" $SDK/package/kernel/mac80211/ $SDK/include/ 2>/dev/null | head -20
echo DONE