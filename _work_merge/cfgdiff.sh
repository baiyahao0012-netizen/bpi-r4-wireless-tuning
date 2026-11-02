#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== diff .config.before-ftrace vs current minimal config ==="
diff $KD/.config.before-ftrace /root/kbuild/linux-6.6.73/.config | head -60
echo "=== diff line count ==="
diff $KD/.config.before-ftrace /root/kbuild/linux-6.6.73/.config | grep -c "^[<>]"
echo "=== DEBUG_INFO in before-ftrace ==="
grep -E "^CONFIG_(DEBUG_INFO|KALLSYMS|JUMP_LABEL|MODULE_UNLOAD|MODULES_TREE_LOOKUP|TRACEPOINTS|FTRACE|KPROBES|FUNCTION_TRACER|MODULE_SIG|LIVEPATCH)=" $KD/.config.before-ftrace | sort
echo DONE
