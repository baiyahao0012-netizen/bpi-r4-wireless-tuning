#!/bin/bash
RD=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
echo "=== fetch user modules from board ==="
for f in mac80211.wdrr.ko tr-mt7996e.ko aplus-mt76.ko; do
  ssh -o StrictHostKeyChecking=no root@192.168.240.1 "cat /root/$f" 2>/dev/null > /root/user_$f
  echo "$f: $(stat -c %s /root/user_$f 2>/dev/null) bytes"
  $RD -SW /root/user_$f 2>/dev/null | grep -i this_module | head -1
done
echo "=== reference sizes ==="
echo -n "stock /rom mac80211: "; $RD -SW /root/stock_mac80211.ko 2>/dev/null | grep -o "this_module.*" | head -1
echo -n "oaf.ko:             "; $RD -SW /root/oaf.ko 2>/dev/null | grep -o "this_module.*" | head -1
echo -n "our mac80211:       "; $RD -SW /root/bpstage/mac80211.ko 2>/dev/null | grep -o "this_module.*" | head -1
echo DONE
