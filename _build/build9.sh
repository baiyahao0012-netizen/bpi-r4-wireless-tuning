#!/bin/bash
# build9: apply WDRR to regular variant + FORCE rebuild (clean) + verify symbols
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== [1/6] apply WDRR patch to REGULAR tree ==="
python3 /root/apply_wdrr.py 2>&1 | tail -8
echo "=== [2/6] verify source ==="
grep -c "flow->quantum ? flow->quantum" "$B/include/net/fq_impl.h"
grep -c "int quantum;" "$B/include/net/fq.h"
grep -c "fq_weight\[IEEE80211_NUM_ACS\]" "$B/net/mac80211/tx.c"
echo "=== [3/6] force clean mac80211 ==="
cd "$SDK"
make package/kernel/mac80211/clean V=s 2>&1 | tail -3
echo "CLEAN_RC=$?"
echo "=== [4/6] compile mac80211 -j24 (full rebuild) ==="
make package/kernel/mac80211/compile V=s -j24 2>&1 | tail -8
echo "COMPILE_RC=${PIPESTATUS[0]}"
echo "=== [5/6] locate ko ==="
find "$SDK/build_dir" -name "mac80211.ko" -path "*regular*" 2>/dev/null | head -3
echo "=== [6/6] symbol verify ==="
KO=$(find "$SDK/build_dir" -name "mac80211.ko" -path "*regular*" 2>/dev/null | head -1)
echo "KO=$KO"
if [ -n "$KO" ]; then
  ls -la "$KO"
  $SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-nm "$KO" 2>/dev/null | grep "fq_weight" | head -6
  strings "$KO" | grep "WDRR" | head -2
fi
echo BUILD9_DONE
