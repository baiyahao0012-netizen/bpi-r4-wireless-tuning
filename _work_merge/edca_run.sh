#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== before: BK params ==="
  iw dev phy0.0-sta0 info 2>/dev/null | grep -i -A2 txq | head -6
  echo "=== run edca_set on STA (AC1=BK) ==="
  /root/edca_set phy0.0-sta0 1 2 1 1 0 2>&1 | head -5
  echo "=== run edca_set on AP (AC3=VO) ==="
  /root/edca_set phy0.0-ap0 3 2 3 7 0 2>&1 | head -5
  echo "=== restore defaults ==="
  /root/edca_set phy0.0-sta0 1 3 4 10 0 2>&1 | head -3
  /root/edca_set phy0.0-ap0 3 2 3 7 0 2>&1 | head -3
  echo "=== dmesg tail (edca/wdrr) ==="
  dmesg | tail -4
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo EDCA3_DONE
