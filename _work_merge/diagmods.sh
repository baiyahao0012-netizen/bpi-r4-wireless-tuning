#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- /tmp/newmods ---"
md5sum /tmp/newmods/lib/modules/6.6.73/mac80211.ko 2>&1
ls -la /tmp/newmods/lib/modules/6.6.73/mac80211.ko 2>&1
echo "--- /overlay/upper ---"
md5sum /overlay/upper/lib/modules/6.6.73/mac80211.ko 2>&1
ls -la /overlay/upper/lib/modules/6.6.73/mac80211.ko 2>&1
echo "--- /lib ---"
ls -la /lib/modules/6.6.73/mac80211.ko 2>&1
echo "--- is /lib/modules a link/mount? ---"
ls -ld /lib/modules /lib/modules/6.6.73 2>&1
cat /proc/mounts | grep -E "modules|/lib"
echo "--- stat both ---"
stat -c "%n %s %y" /overlay/upper/lib/modules/6.6.73/mac80211.ko /lib/modules/6.6.73/mac80211.ko 2>&1
' 2>/dev/null
