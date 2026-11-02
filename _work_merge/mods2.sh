#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- /lib/modules ---"
ls -la /lib/modules/ 2>&1
ls -la /lib/modules/6.6.73/ 2>&1 | head -5
echo "count: $(ls /lib/modules/6.6.73/ | wc -l)"
echo "--- /rom/lib ---"
ls -la /rom/lib/ 2>&1 | head
ls /rom/lib/modules/ 2>&1 | head
echo "rom count: $(ls /rom/lib/modules/6.6.73/ 2>/dev/null | wc -l)"
echo "--- mount ---"
mount | grep -iE "modules|/lib|/rom|/overlay"
echo "--- where is mac80211 ---"
ls -la /lib/modules/6.6.73/mac80211.ko /rom/lib/modules/6.6.73/mac80211.ko 2>&1
echo "--- opkg modules package ---"
ls /usr/lib/opkg/info/ 2>/dev/null | grep -iE "kernel|kmod" | head -10
echo "--- is /lib a symlink? ---"
ls -ld /lib /rom/lib
' 2>/dev/null
