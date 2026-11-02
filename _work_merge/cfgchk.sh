#!/bin/bash
echo "=== minimal config (current) ==="
grep -E "^CONFIG_(DEBUG_INFO|MODULE_UNLOAD|MODULES_TREE_LOOKUP|KALLSYMS|MODULE_SIG|LIVEPATCH|JUMP_LABEL|DEBUG_INFO_BTF|MODULES|MODVERSIONS|TRACEPOINTS|FTRACE|KPROBES|FUNCTION_TRACER|STACKPROTECTOR|RANDOMIZE_BASE)=" /root/kbuild/linux-6.6.73/.config | sort
echo "=== full-ftrace config ==="
grep -E "^CONFIG_(DEBUG_INFO|MODULE_UNLOAD|MODULES_TREE_LOOKUP|KALLSYMS|MODULE_SIG|LIVEPATCH|JUMP_LABEL|DEBUG_INFO_BTF|MODULES|MODVERSIONS)=" /root/config.full-ftrace | sort
echo "=== sizes ==="
wc -l /root/kbuild/linux-6.6.73/.config /root/config.full-ftrace
echo "=== kbuild module count ==="
find /root/kbuild/linux-6.6.73 -name "*.ko" -not -path "*/.tmp_versions/*" | wc -l
echo DONE
