#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== edca_set usage ==="
  /root/edca_set 2>&1 | head -25
  echo "=== edca_set strings hint ==="
  strings /root/edca_set 2>/dev/null | grep -iE "^/(sys|proc)/|debugfs|usage|aifs|cwmin" | head -15
  echo "=== sta_weight (A+ feature) ==="
  cat /sys/kernel/debug/ieee80211/phy0/mt76/sta_weight 2>&1 | head -5
  echo "=== wireless config edca ==="
  uci show wireless 2>/dev/null | grep -iE "edca|aifs|cw|ac_|wmm" | head -10
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo EDCA2_DONE
