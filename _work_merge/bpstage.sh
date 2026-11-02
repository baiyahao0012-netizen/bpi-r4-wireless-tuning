#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic
RD=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
rm -rf /root/bpstage; mkdir -p /root/bpstage
for n in compat cfg80211 mac80211; do
  f=$(find $BD/mac80211-regular -path "*.pkgdir*" -name "$n.ko" 2>/dev/null | head -1)
  [ -n "$f" ] && cp -f "$f" /root/bpstage/$n.ko && echo "got $n.ko $(stat -c %s $f)"
done
TREE=$(ls -d $BD/mt76-2025.01.14~8e4f72b6 2>/dev/null)
[ -n "$TREE" ] && cp -f $TREE/mt76.ko $TREE/mt76-connac-lib.ko /root/bpstage/ 2>/dev/null
[ -n "$TREE" ] && cp -f $TREE/mt7996/mt7996e.ko /root/bpstage/ 2>/dev/null
echo "=== this_module sizes (want 0x480) ==="
for m in /root/bpstage/*.ko; do
  echo "$(basename $m): $($RD -SW $m 2>/dev/null | grep -o 'this_module.*' | head -1)"
done
echo "=== md5 ==="
md5sum /root/bpstage/*.ko
echo BPSTAGE_DONE
