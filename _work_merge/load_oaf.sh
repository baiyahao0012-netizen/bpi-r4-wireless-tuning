#!/bin/bash
B=192.168.240.1
SSH="ssh -o StrictHostKeyChecking=no root@$B"
$SSH '
  cp /root/oaf.ko.new /root/oaf.ko; sync
  md5sum /root/oaf.ko
  echo "--- insmod ---"
  insmod /root/oaf.ko && echo INSOK || echo INSFAIL
  echo "--- proc ---"
  grep "^oaf " /proc/modules
  echo "--- dmesg ---"
  dmesg | tail -6
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo DONE2
