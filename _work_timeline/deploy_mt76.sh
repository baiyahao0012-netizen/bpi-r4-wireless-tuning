#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6

echo "=== scp -O to board ==="
scp -O "$BD/mt76.ko" root@192.168.1.1:/tmp/mt76.ko
scp -O "$BD/mt76-connac-lib.ko" root@192.168.1.1:/tmp/mt76-connac-lib.ko

echo "=== install ==="
ssh root@192.168.1.1 "
cp /tmp/mt76.ko /lib/modules/\$(uname -r)/mt76.ko
cp /tmp/mt76-connac-lib.ko /lib/modules/\$(uname -r)/mt76-connac-lib.ko
echo INSTALLED
"
