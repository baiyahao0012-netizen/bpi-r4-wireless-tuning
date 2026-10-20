#!/bin/bash
# build8: apply WDRR patch (python) + compile mac80211 + locate ko
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
B=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/backports-6.12.6
echo "=== [1/5] apply WDRR patch (python) ==="
python3 /root/apply_wdrr.py 2>&1 | tail -10
echo "=== [2/5] verify ==="
grep -c "flow->quantum ? flow->quantum" "$B/include/net/fq_impl.h"
grep -c "int quantum;" "$B/include/net/fq.h"
grep -c "fq_weight\[IEEE80211_NUM_ACS\]" "$B/net/mac80211/tx.c"
echo "=== [3/5] generate standard diff patch ==="
cd "$B"
diff -u include/net/fq.h.wdrr.orig include/net/fq.h > /root/001-wdrr.patch
diff -u include/net/fq_impl.h.wdrr.orig include/net/fq_impl.h >> /root/001-wdrr.patch
diff -u net/mac80211/tx.c.wdrr.orig net/mac80211/tx.c >> /root/001-wdrr.patch
wc -l /root/001-wdrr.patch
echo "=== [4/5] compile mac80211 (-j24) ==="
cd "$SDK"
make package/kernel/mac80211/compile V=s -j24 2>&1 | tail -6
echo "COMPILE_RC=${PIPESTATUS[0]}"
echo "=== [5/5] locate ko ==="
find "$SDK/build_dir" -name "mac80211.ko" -newer "$B/include/net/fq.h.wdrr.orig" 2>/dev/null | head -3
echo BUILD8_DONE
