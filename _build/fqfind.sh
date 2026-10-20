#!/bin/bash
exec > /root/fqfind.log 2>&1
B=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "B=$B"
echo "=== top-level ==="
ls "$B" | head -25
echo "=== find fq.c ==="
find "$B" -name "fq.c" 2>/dev/null | head -5
echo FQFIND_DONE
