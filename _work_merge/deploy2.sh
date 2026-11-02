#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- copy all via overlay path ---"
n=0
for f in /tmp/newmods/lib/modules/6.6.73/*.ko; do
  cp -f "$f" /lib/modules/6.6.73/ && n=$((n+1))
done
echo "copied: $n"
sync
echo "--- verify key modules via /lib ---"
md5sum /lib/modules/6.6.73/mac80211.ko /lib/modules/6.6.73/mt7996e.ko /lib/modules/6.6.73/cfg80211.ko /lib/modules/6.6.73/mt76.ko /lib/modules/6.6.73/mt76-connac-lib.ko /lib/modules/6.6.73/gpio-button-hotplug.ko
echo "--- verify count ---"
ls /lib/modules/6.6.73/*.ko | wc -l
' 2>/dev/null
echo "=== EXPECTED (local) ==="
md5sum /root/modstage/lib/modules/6.6.73/mac80211.ko /root/modstage/lib/modules/6.6.73/mt7996e.ko /root/modstage/lib/modules/6.6.73/cfg80211.ko /root/modstage/lib/modules/6.6.73/mt76.ko /root/modstage/lib/modules/6.6.73/mt76-connac-lib.ko /root/modstage/lib/modules/6.6.73/gpio-button-hotplug.ko
