#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- full /proc/mounts ---"
cat /proc/mounts
echo "--- test overlay reflection ---"
echo hello > /overlay/upper/zzztest 2>&1
cat /zzztest 2>&1
ls -la /zzztest 2>&1
rm -f /overlay/upper/zzztest
echo "--- lower (/rom) ---"
ls -la /rom/lib/modules/6.6.73/mac80211.ko 2>&1
echo "--- overlay upper dir ---"
ls -la /overlay/upper/lib/modules/6.6.73/ | head -5
echo "--- /lib/modules/6.6.73 mac80211 ---"
ls -la /lib/modules/6.6.73/ | grep -E "mac80211|mt7996|cfg80211|mt76\."
' 2>/dev/null
