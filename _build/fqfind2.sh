#!/bin/bash
exec > /root/fqfind2.log 2>&1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "=== backports net/ ==="
ls "$B/net" 2>/dev/null
echo "=== backports net/mac80211 (fq?) ==="
ls "$B/net/mac80211" 2>/dev/null | head -40
echo "=== kernel source fq.c ==="
ls -la "$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/net/mac80211/fq.c" 2>&1
echo "=== kernel net/mac80211 fq-related ==="
ls "$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/net/mac80211/" 2>/dev/null | grep -i "fq\|txq\|drr"
echo FQFIND2_DONE
