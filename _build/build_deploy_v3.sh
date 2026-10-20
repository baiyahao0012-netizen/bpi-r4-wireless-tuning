#!/bin/bash
set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PATCHDIR=$SDK/package/kernel/mt76/patches
TREE=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
SCP="scp -O -o StrictHostKeyChecking=no -o ConnectTimeout=10"

echo "=== 1. Reset ==="
rm -rf "$TREE"
rm -f "$PATCHDIR/999"*
echo "=== 2. Prepare ==="
make -C "$SDK" package/kernel/mt76/prepare V=s 2>&1 | tail -3

echo "=== 3. Apply v3_final ==="
cp '/mnt/d/Desktop/AI 辅助对话/_build/apply_v3_final.py' /root/apply_v3_final.py
python3 /root/apply_v3_final.py "$TREE"

echo "=== 4. Verify fops has .open=simple_open ==="
grep -A5 'fops_agg_win_cap = {' "$TREE/mt7996/debugfs.c"
grep 'CPTCFG_MAC80211_DEBUGFS' "$TREE/mt7996/debugfs.c"

echo "=== 5. Compile ==="
make -C "$SDK" package/kernel/mt76/compile V=s -j24 > /root/mt76_build_v9.log 2>&1 || true

echo "=== 6. KO check ==="
KO=$TREE/mt7996/mt7996e.ko
if [ -f "$KO" ]; then
  echo "BUILD OK md5=$(md5sum "$KO" | cut -d' ' -f1)"
  nm "$KO" 2>/dev/null | grep -iE 'agg_win_cap_read|agg_win_cap_write|fops_agg_win_cap'
else
  echo "BUILD FAIL"; grep -E 'error:' /root/mt76_build_v9.log | head -10; exit 1
fi

echo "=== 7. Deploy & reboot ==="
$SCP "$KO" root@192.168.1.1:/tmp/mt7996e.ko
$SSH root@192.168.1.1 'cp /tmp/mt7996e.ko /lib/modules/6.6.73/mt7996e.ko; sync; reboot'
echo "DEPLOYED"
