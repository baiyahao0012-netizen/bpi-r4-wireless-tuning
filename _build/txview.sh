#!/bin/bash
exec > /root/txview.log 2>&1
B=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== tx.c 25-40 ==="
sed -n '25,40p' "$B/net/mac80211/tx.c" | cat -A | head -20
echo "=== tx.c 74-84 ==="
sed -n '74,84p' "$B/net/mac80211/tx.c" | cat -A
echo "=== tx.c 1388-1400 ==="
sed -n '1388,1400p' "$B/net/mac80211/tx.c" | cat -A
echo TXVIEW_DONE
