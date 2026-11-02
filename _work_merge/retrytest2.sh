#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== STA state after restore ==="
iw dev phy0.0-sta0 link 2>/dev/null | head -4
sleep 5
iw dev phy0.0-sta0 link 2>/dev/null | head -4
echo "=== enable event ==="
echo 1 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
for pw in 800 600 400 300 200; do
  echo > /sys/kernel/debug/tracing/trace
  iw dev phy0.0-sta0 set txpower fixed $pw 2>/dev/null
  sleep 1
  ping -c 15 -W 1 -i 0.3 192.168.3.1 >/dev/null 2>&1; prc=$?
  n=$(grep -c wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null)
  rn=$(grep wifi_dscp /sys/kernel/debug/tracing/trace 2>/dev/null | grep -oE "retry=[0-9]+" | grep -v "retry=0" | wc -l)
  sig=$(iw dev phy0.0-sta0 link 2>/dev/null | grep -oE "signal:.*" | head -1)
  echo "txpower=$pw ping_rc=$prc events=$n retry_events=$rn $sig"
  if [ "$n" -gt 0 ] && [ "$rn" -gt 0 ]; then
    echo "--- sample retry events ---"
    grep wifi_dscp /sys/kernel/debug/tracing/trace | grep -vE "retry=0" | head -6
  fi
done
iw dev phy0.0-sta0 set txpower auto 2>/dev/null
echo 0 > /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/enable
sleep 2
iw dev phy0.0-sta0 info 2>/dev/null | grep -i txpower
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
