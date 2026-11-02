#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- available_events count ---"
wc -l < /sys/kernel/debug/tracing/available_events
echo "--- events dirs ---"
ls /sys/kernel/debug/tracing/events/ | head -40
echo "--- mac80211 events? ---"
ls /sys/kernel/debug/tracing/events/mac80211/ 2>&1 | head
echo "--- available_tracers ---"
cat /sys/kernel/debug/tracing/available_tracers
echo "--- modules ---"
cat /proc/modules | head -25
echo "--- mac80211.ko md5 on board ---"
md5sum /lib/modules/6.6.73/mac80211.ko /lib/modules/6.6.73/cfg80211.ko 2>&1
echo "--- wifi ---"
iw dev 2>&1 | head -20
' 2>/dev/null
