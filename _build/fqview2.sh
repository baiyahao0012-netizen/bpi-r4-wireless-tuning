#!/bin/bash
exec > /root/fqview2.log 2>&1
B=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "=== fq_impl.h 85-140 (dequeue+DRR) ==="
sed -n '85,140p' "$B/include/net/fq_impl.h"
echo "=== fq_impl.h 330,365 (flow_init/fq_init) ==="
sed -n '330,365p' "$B/include/net/fq_impl.h"
echo "=== fq.h 26-45 (struct fq_flow) ==="
sed -n '26,45p' "$B/include/net/fq.h"
echo "=== tx.c 1385-1415 (fq_tin_dequeue_func) ==="
sed -n '1385,1415p' "$B/net/mac80211/tx.c"
echo "=== tx.c top (module param area) ==="
sed -n '1,40p' "$B/net/mac80211/tx.c" | grep -n "module_param\|MODULE\|static" 
echo "=== tx.c 3850-3860 (dequeue call) ==="
sed -n '3845,3860p' "$B/net/mac80211/tx.c"
echo FQVIEW2_DONE
