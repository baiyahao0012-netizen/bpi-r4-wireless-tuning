#!/bin/bash
B=192.168.240.1
S="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@$B"
echo '=== rebooting ==='
$S 'sync; reboot' 2>/dev/null
sleep 15
echo '=== waiting for board ==='
UP=0
for i in $(seq 1 60); do
  if $S 'echo up' 2>/dev/null | grep -q up; then UP=1; echo "board back after ~$((15+i*5))s"; break; fi
  sleep 5
done
[ $UP -eq 1 ] || { echo 'BOARD DID NOT COME BACK'; exit 1; }
sleep 20
$S '
  echo "=== uptime ==="
  uptime
  echo "=== kernel ==="
  uname -r
  echo "=== modules ==="
  echo "count: $(wc -l < /proc/modules)"
  echo "oaf: $(grep -c \"^oaf \" /proc/modules)"
  grep -E "^(mt7996e|mac80211|mt76|cfg80211) " /proc/modules | awk "{print \$1}" | tr "\n" " "; echo
  echo "=== oaf section-size errors this boot ==="
  dmesg | grep -c "section size must match"
  dmesg | grep "section size must match" | sed -E "s/.*module ([a-z0-9_]+):.*/\1/" | sort -u | tr "\n" " "; echo
  echo "=== tracepoint ==="
  ls -d /sys/kernel/debug/tracing/events/mac80211/wifi_dscp 2>&1
  echo "=== fwx proc ==="
  ls /proc/sys/fwx/ 2>/dev/null | tr "\n" " "; echo
  echo "=== wifi ==="
  iw dev 2>/dev/null | grep -E "Interface|ssid" | head -8
  echo "=== sta link ==="
  iw dev phy0.0-sta0 link 2>/dev/null | grep -E "Connected|SSID|signal"
  echo "=== ping ==="
  ping -c 3 -W 2 192.168.3.1 2>&1 | tail -1
  echo "=== wdrr ==="
  dmesg | grep -i wdrr | tail -2
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo REBOOT_TEST_DONE
