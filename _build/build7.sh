#!/bin/bash
exec > /root/build7.log 2>&1
export http_proxy=http://172.25.112.1:7897
export https_proxy=http://172.25.112.1:7897
export NO_PROXY=localhost,127.0.0.1
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "=== [1] apply patch (dry-run first) ==="
cd "$B"
patch -p1 --dry-run < /root/001-wdrr.patch 2>&1 | tail -8
echo "DRY_RUN_RC=$?"
echo "=== [2] real apply ==="
patch -p1 < /root/001-wdrr.patch 2>&1 | tail -8
echo "APPLY_RC=$?"
echo "=== [3] verify changes ==="
grep -n "flow->quantum ? flow->quantum" "$B/include/net/fq_impl.h"
grep -n "int quantum;" "$B/include/net/fq.h"
grep -n "fq_weight\[IEEE80211_NUM_ACS\]" "$B/net/mac80211/tx.c"
grep -n "Private WDRR" "$B/net/mac80211/tx.c" | head -3
echo "=== [4] compile mac80211 (8-core) ==="
cd "$SDK"
make package/kernel/mac80211/compile V=s -j$(nproc) 2>&1 | tail -20
echo "COMPILE_PIPE_RC=${PIPESTATUS[0]}"
echo "=== [5] locate mac80211.ko ==="
find "$SDK/build_dir" -name "mac80211.ko" 2>/dev/null | head -5
echo BUILD7_DONE
