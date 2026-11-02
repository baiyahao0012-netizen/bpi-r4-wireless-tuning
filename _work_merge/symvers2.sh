#!/bin/bash
KD=/root/kbuild/linux-6.6.73
echo "=== vmlinux / vmlinux.symvers / Module.symvers in new tree ==="
ls -la $KD/vmlinux $KD/vmlinux.symvers $KD/Module.symvers $KD/vmlinux.o 2>&1
echo "=== .tmp_vmlinux* ==="
ls -la $KD/.tmp_vmlinux* 2>&1 | head
echo "=== check SDK Module.symvers for consume_skb exact line ==="
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
grep "consume_skb" $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/Module.symvers
echo "=== CONFIG_MODVERSIONS in new .config ==="
grep "CONFIG_MODVERSIONS" $KD/.config
echo "=== count of exported syms in SDK Module.symvers ==="
wc -l $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/Module.symvers
echo DONE
