#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== SDK kernel file count ==="
find $KD -type f | wc -l
echo "=== top-level entries ==="
ls $KD | tr '\n' ' '
echo
echo "=== missing top-level dirs vs a standard tree ==="
for d in Documentation certs init io_uring ipc rust samples usr virt; do
  [ -d "$KD/$d" ] && echo "PRESENT $d" || echo "MISSING $d"
done
echo DONE
