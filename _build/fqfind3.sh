#!/bin/bash
exec > /root/fqfind3.log 2>&1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
K=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== grep fq_tin_deficit in backports ==="
grep -rn "fq_tin_deficit\|fq_flow_deficit\|deficit" "$B/net/mac80211/" 2>/dev/null | head -20
echo "=== grep fq_tin_deficit in kernel ==="
grep -rn "fq_tin_deficit\|fq_flow_deficit\|deficit" "$K/net/mac80211/" 2>/dev/null | head -20
echo "=== ls kernel net/mac80211 f*.c ==="
ls "$K/net/mac80211/" | grep -E "^f"
echo "=== grep fq in kernel tx.c ==="
grep -n "fq\b\|fq_tin\|fq_flow" "$K/net/mac80211/tx.c" 2>/dev/null | head -25
echo FQFIND3_DONE
