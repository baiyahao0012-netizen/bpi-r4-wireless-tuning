#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=6 root@$B"
$S '
  echo "=== why STA -EINVAL: STA iface is not AP/P2P (mac80211 only allows set_txq on AP-like) ==="
  echo "--- test on AP with all 4 ACs ---"
  for ac in 0 1 2 3; do /root/edca_set phy0.0-ap0 $ac 2 3 7 0 2>&1 | head -1; done
  echo "--- restore AP ACs to standard values ---"
  /root/edca_set phy0.0-ap0 0 3 4 10 0 >/dev/null 2>&1
  /root/edca_set phy0.0-ap0 1 7 4 10 0 >/dev/null 2>&1
  /root/edca_set phy0.0-ap0 2 2 3 4 94 >/dev/null 2>&1
  /root/edca_set phy0.0-ap0 3 2 2 3 47 >/dev/null 2>&1
  echo restored
  echo "=== AP AC verification after restore ==="
  for ac in 0 1 2 3; do /root/edca_set phy0.0-ap0 $ac 2>&1 | head -1; done
  echo "=== dscp tracepoint still fine after edca ops ==="
  echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
  echo > /sys/kernel/debug/tracing/trace
  nft delete table inet dsct 2>/dev/null; nft add table inet dsct
  nft add chain inet dsct out "{ type route hook output priority mangle; }"
  nft add rule inet dsct out ip protocol icmp ip dscp set af41
  ping -c 6 -W 2 192.168.3.1 >/dev/null 2>&1
  sleep 1
  echo events=$(grep -c wifi_dscp /sys/kernel/debug/tracing/trace)
  grep wifi_dscp /sys/kernel/debug/tracing/trace | head -4
  echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
  nft delete table inet dsct 2>/dev/null
  echo "=== oaf still ok ==="
  cat /proc/sys/fwx/appfilter_enable
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo EDCA4_DONE
