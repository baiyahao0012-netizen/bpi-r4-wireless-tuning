#!/bin/bash
B=192.168.240.1
SSH="ssh -o StrictHostKeyChecking=no root@$B"
$SSH '
  echo "=== module info ==="
  cat /sys/module/oaf/refcnt 2>/dev/null
  ls /sys/module/oaf/ 2>/dev/null | tr "\n" " "; echo
  echo "=== proc/sysfs interface ==="
  ls /proc 2>/dev/null | grep -i -E "oaf|fwx" | tr "\n" " "; echo
  ls /sys/kernel/debug/ 2>/dev/null | grep -i -E "oaf|fwx" | tr "\n" " "; echo
  echo "=== dmesg oaf/fwx ==="
  dmesg | grep -iE "oaf|fwx" | tail -5
  echo "=== init.d ==="
  ls -la /etc/init.d/oaf-mini /root/oaf_start.sh 2>/dev/null
  echo "=== fwxd / oafd running? ==="
  ps w 2>/dev/null | grep -iE "oaf|fwx" | grep -v grep
  echo "=== netfilter hooks ==="
  cat /proc/net/netfilter/nf_log 2>/dev/null | head -3
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo DONE3
