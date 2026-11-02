#!/bin/bash
B=192.168.240.1
SSH="ssh -o StrictHostKeyChecking=no root@$B"
$SSH '
  echo "=== /proc/sys/fwx ==="
  ls -la /proc/sys/fwx/ 2>&1 | head -12
  echo "=== appfilter_enable ==="
  cat /proc/sys/fwx/appfilter_enable 2>&1
  echo "=== feature_init ==="
  cat /proc/sys/fwx/feature_init 2>&1
  echo "=== trigger enable ==="
  echo 1 > /proc/sys/fwx/appfilter_enable && echo "set ok" || echo "set fail"
  echo 1 > /proc/sys/fwx/feature_init && echo "feat ok" || echo "feat fail"
  echo "=== oaf modules ==="
  grep "^oaf " /proc/modules
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo DONE5
