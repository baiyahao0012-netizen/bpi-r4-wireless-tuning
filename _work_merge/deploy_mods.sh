#!/bin/bash
cd /root/modstage
echo "=== local md5 of key modules ==="
md5sum lib/modules/6.6.73/mac80211.ko lib/modules/6.6.73/mt7996e.ko lib/modules/6.6.73/cfg80211.ko lib/modules/6.6.73/mt76.ko
echo "=== pack ==="
tar czf /root/modules-new.tar.gz lib
ls -la /root/modules-new.tar.gz
echo "=== transfer ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'rm -rf /tmp/newmods; mkdir -p /tmp/newmods; cd /tmp/newmods && tar xzf -' < /root/modules-new.tar.gz
echo "transfer rc=$?"
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
  echo "--- extracted: $(ls /tmp/newmods/lib/modules/6.6.73/*.ko | wc -l) ---"
  mkdir -p /overlay/upper/lib/modules/6.6.73
  cp -f /tmp/newmods/lib/modules/6.6.73/*.ko /overlay/upper/lib/modules/6.6.73/
  sync
  echo "--- overlay .ko: $(ls /overlay/upper/lib/modules/6.6.73/*.ko | wc -l) ---"
  echo "--- merged .ko: $(ls /lib/modules/6.6.73/*.ko | wc -l) ---"
  echo "--- board md5 ---"
  md5sum /lib/modules/6.6.73/mac80211.ko /lib/modules/6.6.73/mt7996e.ko /lib/modules/6.6.73/cfg80211.ko /lib/modules/6.6.73/mt76.ko
'
echo DEPLOY_DONE
