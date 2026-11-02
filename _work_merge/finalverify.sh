#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "########## FINAL VERIFICATION ##########"
echo "=== 1. kernel ==="
uname -a
echo "=== 2. modules loaded ==="
echo "count: $(wc -l < /proc/modules)"
grep -E "^(mt7996e|mt76|mt76_connac_lib|mac80211|cfg80211|compat) " /proc/modules
echo "=== 3. tracepoint ==="
ls -d /sys/kernel/debug/tracing/events/mac80211/wifi_dscp 2>&1
cat /sys/kernel/debug/tracing/events/mac80211/wifi_dscp/id 2>/dev/null
echo "=== 4. wifi ifaces ==="
iw dev 2>/dev/null | grep -E "Interface|ssid|channel" | head -12
echo "=== 5. sta link ==="
iw dev phy0.0-sta0 link 2>/dev/null | head -5
echo "=== 6. connectivity ==="
ping -c 5 -W 2 192.168.3.1 2>&1 | tail -2
echo "=== 7. overlay space ==="
df -h /overlay | tail -1
echo "=== 8. residual module errors ==="
dmesg | grep -c "section size must match"
dmesg | grep "section size must match" | sed -E "s/.*module ([a-z0-9_]+):.*/\1/" | sort -u | tr "\n" " "; echo
echo "=== 9. dscpstats present ==="
ls -la /tmp/dscptest/dscptest/dscpstats 2>&1
echo "=== 10. uptime ==="
uptime
' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
