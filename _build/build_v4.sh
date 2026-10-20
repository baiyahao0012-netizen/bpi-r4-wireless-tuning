#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PATCHDIR=$SDK/package/kernel/mt76/patches
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
SCP="scp -O -o StrictHostKeyChecking=no -o ConnectTimeout=10"
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"

echo "=== reset ==="
rm -rf "$TREE"; rm -f "$PATCHDIR/999"*
make -C "$SDK" package/kernel/mt76/prepare V=s 2>&1 | tail -2

echo "=== apply v4_final ==="
cp '/mnt/d/Desktop/AI 辅助对话/_build/apply_v4_final.py' /root/apply_v4_final.py
python3 /root/apply_v4_final.py "$TREE"

echo "=== compile ==="
make -C "$SDK" package/kernel/mt76/compile V=s -j24 > /root/mt76_build_v4.log 2>&1 || true
KO=$TREE/mt7996/mt7996e.ko
if [ -f "$KO" ]; then
  echo "BUILD OK md5=$(md5sum "$KO"|cut -d' ' -f1)"
else
  echo "BUILD FAIL"; grep -E 'error:' /root/mt76_build_v4.log | head -15; exit 1
fi

echo "=== deploy ==="
$SCP "$KO" root@192.168.1.1:/tmp/mt7996e.ko
$SSH root@192.168.1.1 'cp /tmp/mt7996e.ko /lib/modules/6.6.73/mt7996e.ko; sync; reboot'
echo "DEPLOYED+REBOOT"
