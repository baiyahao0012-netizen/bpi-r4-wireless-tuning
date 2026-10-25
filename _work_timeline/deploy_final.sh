#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
BOARD=root@192.168.240.1

echo "=== scp new ko ==="
scp -O "$BD/mt76.ko" $BOARD:/tmp/mt76_new.ko
scp -O "$BD/mt76-connac-lib.ko" $BOARD:/tmp/mt76-connac-lib_new.ko

echo "=== install ==="
ssh $BOARD "
KVER=\$(uname -r)
# backup
cp /lib/modules/\$KVER/mt76.ko /lib/modules/\$KVER/mt76.ko.old
cp /lib/modules/\$KVER/mt76-connac-lib.ko /lib/modules/\$KVER/mt76-connac-lib.ko.old
# install new
cp /tmp/mt76_new.ko /lib/modules/\$KVER/mt76.ko
cp /tmp/mt76-connac-lib_new.ko /lib/modules/\$KVER/mt76-connac-lib.ko
echo INSTALLED_NEED_REBOOT
"
