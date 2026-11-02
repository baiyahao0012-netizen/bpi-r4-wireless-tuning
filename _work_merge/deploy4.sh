#!/bin/bash
for i in $(seq 1 12); do
  sleep 25
  R=$(ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat /tmp/copymods.done 2>/dev/null; ps | grep -c "[c]opymods"' 2>/dev/null | tr "\n" " ")
  echo "poll $i: $R"
  case "$R" in *COPIED*) break;; esac
done
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- final md5 ---"
md5sum /lib/modules/6.6.73/mac80211.ko /lib/modules/6.6.73/mt7996e.ko /lib/modules/6.6.73/cfg80211.ko /lib/modules/6.6.73/mt76.ko /lib/modules/6.6.73/mt76-connac-lib.ko
' 2>/dev/null
