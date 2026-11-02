#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- A: write via overlay path /lib/... ---"
cp -f /tmp/newmods/lib/modules/6.6.73/cfg80211.ko /lib/modules/6.6.73/cfg80211.ko
echo "via /lib : $(md5sum /lib/modules/6.6.73/cfg80211.ko | cut -d" " -f1)"
echo "upper    : $(md5sum /overlay/upper/lib/modules/6.6.73/cfg80211.ko | cut -d" " -f1)"
echo "--- B: new file via overlay lands in upper? ---"
echo t2 > /lib/modules/6.6.73/zz2.txt
ls -la /overlay/upper/lib/modules/6.6.73/zz2.txt 2>&1
rm -f /lib/modules/6.6.73/zz2.txt
echo "--- C: read upper file directly vs via / ---"
cp /overlay/upper/lib/modules/6.6.73/mac80211.ko /tmp/u1
md5sum /tmp/u1
cp /lib/modules/6.6.73/mac80211.ko /tmp/u2
md5sum /tmp/u2
echo "--- D: /lib dir listing of act_csum ---"
ls -la /lib/modules/6.6.73/act_csum.ko /overlay/upper/lib/modules/6.6.73/act_csum.ko
' 2>/dev/null
