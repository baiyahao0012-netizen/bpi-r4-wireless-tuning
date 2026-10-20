#!/bin/bash
# build10: prepare (fresh source) -> apply WDRR to BOTH variants -> force compile -> verify
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
PREP=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic
echo "=== [1/7] clean + prepare (fresh source trees) ==="
cd "$SDK"
make package/kernel/mac80211/clean V=s 2>&1 | tail -2
make package/kernel/mac80211/prepare V=s 2>&1 | tail -3
echo "PREPARE_RC=$?"
echo "=== [2/7] confirm both trees have fq.h ==="
ls "$PREP/mac80211-regular/backports-6.12.6/include/net/fq.h" "$PREP/mac80211-smallbuffers/backports-6.12.6/include/net/fq.h" 2>&1
echo "=== [3/7] apply WDRR to BOTH variants ==="
for V in mac80211-regular mac80211-smallbuffers; do
  echo "--- apply to $V ---"
  python3 /root/apply_wdrr.py "$PREP/$V/backports-6.12.6" 2>&1 | tail -3
done
echo "=== [4/7] verify source (regular) ==="
B="$PREP/mac80211-regular/backports-6.12.6"
grep -c "flow->quantum ? flow->quantum" "$B/include/net/fq_impl.h"
grep -c "int quantum;" "$B/include/net/fq.h"
grep -c "fq_weight\[IEEE80211_NUM_ACS\]" "$B/net/mac80211/tx.c"
grep -c "flow->quantum = fq->quantum \* w" "$B/net/mac80211/tx.c"
echo "=== [5/7] compile -j24 (full rebuild) ==="
make package/kernel/mac80211/compile V=s -j24 2>&1 | tail -6
echo "COMPILE_RC=${PIPESTATUS[0]}"
echo "=== [6/7] locate ko ==="
find "$PREP" -name "mac80211.ko" 2>/dev/null | head -4
echo "=== [7/7] symbol verify ==="
for K in $(find "$PREP" -name "mac80211.ko" 2>/dev/null); do
  echo "--- $K ---"
  $SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-nm "$K" 2>/dev/null | grep "fq_weight" | head -4
  strings "$K" | grep "WDRR" | head -1
done
echo BUILD10_DONE
