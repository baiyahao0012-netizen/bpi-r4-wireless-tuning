#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== .config backups in SDK kernel tree ==="
ls -la $KD/.config* 2>&1
echo "=== SDK top-level configs ==="
ls -la $SDK/.config* 2>&1
echo "=== any config-6.6 in SDK target ==="
find $SDK/target/linux/mediatek -name "config-*" 2>/dev/null
echo "=== generic config ==="
ls $SDK/target/linux/generic/config-6.6 2>&1
echo "=== grep struct-module-relevant options in SDK target configs ==="
for f in $SDK/target/linux/generic/config-6.6 $SDK/target/linux/mediatek/config-6.6 $SDK/target/linux/mediatek/filogic/config-6.6; do
  [ -f "$f" ] && echo "--- $f ---" && grep -E "MODULE_UNLOAD|KALLSYMS|MODULES_TREE_LOOKUP|JUMP_LABEL|TRACEPOINTS|MODULE_SIG|LIVEPATCH" "$f" | head
done
echo DONE
