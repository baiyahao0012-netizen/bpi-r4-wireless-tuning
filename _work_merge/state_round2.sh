#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== uptime/kernel ==="
  uptime; uname -r
  echo "=== modules ==="
  echo count=$(wc -l < /proc/modules)
  grep -E "^(oaf|mt7996e|mt76|mt76_connac_lib|mac80211|cfg80211|compat) " /proc/modules | awk "{print \$1, \$2}"
  echo "=== tracepoint ==="
  ls -d /sys/kernel/debug/tracing/events/mac80211/wifi_dscp 2>&1
  echo "=== fwx ==="
  cat /proc/sys/fwx/appfilter_enable 2>/dev/null; ls /proc/sys/fwx 2>/dev/null | wc -l
  echo "=== wifi/sta ==="
  iw dev phy0.0-sta0 link 2>/dev/null | grep -E "Connected|SSID|signal"
  ping -c 3 -W 2 192.168.3.1 2>&1 | tail -1
  echo "=== section-size errors ==="
  dmesg | grep "section size must match" | sed -E "s/.*module ([a-z0-9_]+):.*/\1/" | sort -u | tr "\n" " "; echo
  echo "=== overlay ==="
  df -h /overlay | tail -1
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo STATE_DONE
