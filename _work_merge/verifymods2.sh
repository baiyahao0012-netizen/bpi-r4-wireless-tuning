#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cd /overlay/upper/lib/modules/6.6.73 && md5sum *.ko' 2>/dev/null > /root/board_upper_md5.txt
wc -l < /root/board_upper_md5.txt
# normalize: name md5
awk '{print $2" "$1}' /root/local_md5.txt | sort > /tmp/l.txt
awk '{print $2" "$1}' /root/board_upper_md5.txt | sort > /tmp/b.txt
echo "=== mismatches ==="
diff /tmp/l.txt /tmp/b.txt && echo "*** ALL 103 IDENTICAL ***"
echo "=== spot check ==="
grep -E "mac80211.ko|mt7996e.ko|cfg80211.ko|mt76.ko|gpio-button" /tmp/b.txt
echo DONE
