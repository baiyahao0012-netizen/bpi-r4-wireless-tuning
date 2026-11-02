#!/bin/bash
NEW=/root/kbuild/linux-6.6.73
echo "=== full FIT dts ==="
$NEW/scripts/dtc/dtc -I dtb -O dts /root/fit.dtb 2>/dev/null | grep -E "data-size|data-offset|^\s+[a-z].*\{|description|compression|type" | head -80
echo "=== mac80211 rebuild progress ==="
tail -3 /root/mac80211_out.log 2>/dev/null
tail -3 /root/mac80211_build2.log 2>/dev/null
echo DONE
