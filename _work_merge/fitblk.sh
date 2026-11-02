#!/bin/bash
KD=/root/kbuild/linux-6.6.73
echo "=== mac80211 rebuild result ==="
tail -20 /root/mac80211_out.log
echo "=== fitblk driver source ==="
find $KD -name "*fitblk*" 2>/dev/null
echo "=== board fit0/fitrw geometry ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
for d in fit0 fitrw; do
  echo "$d: start=$(cat /sys/class/block/$d/start) size=$(cat /sys/class/block/$d/size)"
done
echo "p7: start=$(cat /sys/class/block/mmcblk0p7/start) size=$(cat /sys/class/block/mmcblk0p7/size)"
echo "--- device-tree fitblk node ---"
ls /proc/device-tree/ | head -30
find /proc/device-tree -name "*fitblk*" 2>/dev/null
' 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo DONE
