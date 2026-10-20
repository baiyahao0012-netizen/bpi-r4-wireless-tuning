#!/bin/bash
exec > /root/fqfind4.log 2>&1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
K=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== search fq_codel/fq_sched in backports (all) ==="
grep -rn "fq_sched_data\|fq_codel\|fq_flow_deficit" "$B" 2>/dev/null | head -15
echo "=== backports include/net/fq* ==="
ls "$B/include/net/" | grep -i fq
echo "=== kernel tree net/mac80211 exists? ==="
ls -d "$K/net/mac80211" 2>&1
ls "$K/net/" 2>/dev/null | head -20
echo "=== kernel include/net/fq* ==="
ls "$K/include/net/" 2>/dev/null | grep -i fq
echo "=== kernel fq.c anywhere ==="
find "$K" -maxdepth 3 -name "fq.c" 2>/dev/null | head -5
echo FQFIND4_DONE
