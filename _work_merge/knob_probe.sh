#!/bin/bash
B=192.168.240.1
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B 'command -v tc || echo no-tc; echo ---; ls -l /sys/kernel/debug/ieee80211/phy0/mt76/ | awk "{print \$1, \$9}" | head -22' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh"
echo KNOB_DONE
