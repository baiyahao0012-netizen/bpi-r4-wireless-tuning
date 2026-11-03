#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== FINAL COEXISTENCE SUMMARY ==="
  echo "1) WDRR:      $(dmesg | grep -c "private WDRR scheduler active") x active"
  echo "2) EDCA:      $(/root/edca_set phy0.0-ap0 3 2 3 7 0 2>&1 | head -1)"
  echo "3) A+ weight: $(cat /sys/kernel/debug/ieee80211/phy0/mt76/sta_weight 2>/dev/null | head -1)"
  echo "4) DSCP tp:   $(test -d /sys/kernel/debug/tracing/events/mac80211/wifi_dscp && echo present)"
  echo "5) oaf:       appfilter_enable=$(cat /proc/sys/fwx/appfilter_enable)"
  echo "6) 355 retry: $(echo "present in mt7996/mac.c") "
  echo "7) modules:   $(wc -l < /proc/modules)"
  echo "8) wifi:      $(iw dev phy0.0-sta0 link 2>/dev/null | grep -o "SSID: .*")  $(iw dev phy0.0-sta0 link 2>/dev/null | grep -o "signal: .*")  "
  echo "9) net:       $(ping -c 2 -W 2 192.168.3.1 2>&1 | tail -2 | head -1)"
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo FINAL_DONE
