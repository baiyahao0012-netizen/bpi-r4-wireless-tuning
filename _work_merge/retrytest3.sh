#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
nft delete table inet dsctest 2>/dev/null
nft add table inet dsctest
nft add chain inet dsctest out "{ type route hook output priority mangle; }"
nft add rule inet dsctest out ip protocol icmp ip dscp set af41
echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
echo "=== baseline full power ==="
echo > /sys/kernel/debug/tracing/trace
ping -c 10 -W 2 192.168.3.1 >/dev/null 2>&1
echo "events=$(grep -c wifi_dscp /sys/kernel/debug/tracing/trace)"
for pw in 700 600 500 450 400; do
  echo > /sys/kernel/debug/tracing/trace
  iw dev phy0.0-sta0 set txpower fixed $pw 2>/dev/null
  sleep 1
  ping -c 20 -W 2 -i 0.4 192.168.3.1 >/dev/null 2>&1; prc=$?
  sleep 1
  n=$(grep -c wifi_dscp /sys/kernel/debug/tracing/trace)
  rn=$(grep wifi_dscp /sys/kernel/debug/tracing/trace | grep -oE "retry=[0-9]+" | grep -v "retry=0" | wc -l)
  echo "txpower=$pw ping_rc=$prc events=$n retry_events=$rn"
  if [ "$rn" -gt 0 ]; then grep wifi_dscp /sys/kernel/debug/tracing/trace | grep -vE "retry=0" | head -5; break; fi
done
iw dev phy0.0-sta0 set txpower auto 2>/dev/null
echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
nft delete table inet dsctest 2>/dev/null
sleep 2; iw dev phy0.0-sta0 info 2>/dev/null | grep -i txpower
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
