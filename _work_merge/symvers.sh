#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== SDK kernel Module.symvers ==="
ls -la $KD/Module.symvers 2>&1
wc -l $KD/Module.symvers 2>&1
grep -c "consume_skb" $KD/Module.symvers 2>&1
echo "=== new tree Module.symvers ==="
ls -la /root/kbuild/linux-6.6.73/Module.symvers 2>&1
echo "=== backports Module.symvers ==="
ls -la $BP/Module.symvers 2>&1
wc -l $BP/Module.symvers 2>&1
echo "=== vmlinux ==="
ls -la $KD/vmlinux 2>&1
echo "=== SDK kernel dir listing (top) ==="
ls $KD | tr '\n' ' '
echo
echo "=== all Module.symvers under SDK build_dir ==="
find $SDK/build_dir -maxdepth 4 -name "Module.symvers" 2>/dev/null | head
echo "=== does .config in KD have tracing? ==="
grep -c "CONFIG_TRACEPOINTS=y" $KD/.config
echo DONE
