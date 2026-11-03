#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== edca_set present? ==="
  ls -la /root/edca_set /usr/bin/edca_set /lib/modules/*/edca_set 2>/dev/null
  command -v edca_set
  echo "=== mt7996 debugfs tree ==="
  find /sys/kernel/debug/ieee80211 -maxdepth 3 -type d 2>/dev/null | head -20
  echo "=== mt76 debugfs files ==="
  ls /sys/kernel/debug/ieee80211/phy0/mt76/ 2>/dev/null | tr "\n" " "; echo
  echo "=== edca-related files ==="
  find /sys/kernel/debug/ieee80211 -name "*edca*" -o -name "*aifs*" -o -name "*cw*" 2>/dev/null | head -20
  echo "=== /root scripts ==="
  ls /root/*.sh 2>/dev/null | tr "\n" " "; echo
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo EDCA_DONE
