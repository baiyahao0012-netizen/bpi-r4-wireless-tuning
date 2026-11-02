#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat /rom/lib/modules/6.6.73/mac80211.ko' 2>/dev/null > /root/stock_mac80211.ko
ls -la /root/stock_mac80211.ko
RD=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
echo "=== stock /rom mac80211.ko ==="
$RD -SW /root/stock_mac80211.ko 2>/dev/null | grep -i this_module
echo "=== oaf.ko ==="
$RD -SW /root/oaf.ko 2>/dev/null | grep -i this_module
echo "=== our rebuilt mac80211.ko ==="
$RD -SW /root/modstage/lib/modules/6.6.73/mac80211.ko 2>/dev/null | grep -i this_module
echo "=== other board backups in /root ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'ls -la /root/*.ko | head -20' 2>/dev/null
echo DONE
