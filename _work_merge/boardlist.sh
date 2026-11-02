#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'ls /lib/modules/6.6.73/' 2>/dev/null | grep '\.ko$' | grep -vE '\.(stock|bak_combo|combo|pre_mcs|diag)$' | sort > /root/board_mods.txt
echo "board modules: $(wc -l < /root/board_mods.txt)"
echo "--- non-backports (kernel tree) ---"
grep -vE '^(cfg80211|mac80211|compat|mt76|mt76-connac-lib|mt7996e)\.ko$' /root/board_mods.txt | tr '\n' ' '
echo
echo "--- backports ---"
grep -E '^(cfg80211|mac80211|compat|mt76|mt76-connac-lib|mt7996e)\.ko$' /root/board_mods.txt | tr '\n' ' '
echo
echo "--- check each exists in kbuild ---"
miss=0
while read m; do
  case "$m" in cfg80211.ko|mac80211.ko|compat.ko|mt76.ko|mt76-connac-lib.ko|mt7996e.ko) continue;; esac
  f=$(find /root/kbuild/linux-6.6.73 -name "$m" -not -path "*/.tmp_versions/*" 2>/dev/null | head -1)
  if [ -z "$f" ]; then echo "MISSING: $m"; miss=$((miss+1)); fi
done < /root/board_mods.txt
echo "missing count: $miss"
