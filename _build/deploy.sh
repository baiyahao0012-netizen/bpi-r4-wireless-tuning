#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt7996/mt7996e.ko
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
SCP="scp -O -o StrictHostKeyChecking=no -o ConnectTimeout=10"

echo "=== 1. Deploy KO to board ==="
echo "Local MD5: $(md5sum "$KO" | cut -d' ' -f1)"
$SCP "$KO" root@192.168.1.1:/tmp/mt7996e.ko

echo "=== 2. Backup orig (if not yet) + deploy + reboot ==="
$SSH root@192.168.1.1 '
  md5sum /tmp/mt7996e.ko
  ls -la /lib/modules/6.6.73/mt7996e.ko.orig 2>/dev/null || cp /lib/modules/6.6.73/mt7996e.ko /lib/modules/6.6.73/mt7996e.ko.orig
  cp /tmp/mt7996e.ko /lib/modules/6.6.73/mt7996e.ko
  sync
  echo "DEPLOYED"
  reboot
'
echo "=== Board rebooting... ==="
