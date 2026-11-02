#!/bin/bash
cd /root/bpstage
echo "=== LOCAL md5 ==="
md5sum *.ko
tar czf /root/bp.tar.gz *.ko
ls -la /root/bp.tar.gz
echo "=== transfer ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'rm -rf /tmp/bp; mkdir -p /tmp/bp; cd /tmp/bp && tar xzf -' < /root/bp.tar.gz
echo "rc=$?"
echo "=== install to /overlay/upper (direct) ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
  for f in /tmp/bp/*.ko; do cp -f "$f" /overlay/upper/lib/modules/6.6.73/; done
  sync
  echo "--- board upper md5 ---"
  md5sum /overlay/upper/lib/modules/6.6.73/compat.ko /overlay/upper/lib/modules/6.6.73/cfg80211.ko /overlay/upper/lib/modules/6.6.73/mac80211.ko /overlay/upper/lib/modules/6.6.73/mt76.ko /overlay/upper/lib/modules/6.6.73/mt76-connac-lib.ko /overlay/upper/lib/modules/6.6.73/mt7996e.ko
  echo "--- total in upper: $(ls /overlay/upper/lib/modules/6.6.73/*.ko | wc -l) ---"
' 2>/dev/null
echo DEPLOY_BP_DONE
