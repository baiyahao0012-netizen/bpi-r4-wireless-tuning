#!/bin/bash
exec > /root/fqview.log 2>&1
B=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "=== fq_impl.h DRR functions ==="
grep -n "deficit\|quantum\|fq_tin_deficit\|fq_flow_deficit\|static.*fq" "$B/include/net/fq_impl.h" | head -40
echo "=== fq.h key structs ==="
grep -n "struct fq_sched_data\|struct fq_tin\|struct fq_flow\|quantum\|deficit" "$B/include/net/fq.h" | head -30
echo "=== tx.c fq instantiation ==="
grep -n "FQ_\|fq_impl\|fq_tin\|fq_sched_data\|fq_flow" "$B/net/mac80211/tx.c" | head -30
echo FQVIEW_DONE
