#!/bin/bash
# Stability probe v2: preflight + 30 s ping + AP counter deltas.
IF=wlan0
AP=192.168.240.1
MAC=90:de:80:1c:6a:7a
apstat() {
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@$AP \
    "iw dev phy0.1-ap0 station dump | sed -n '/$MAC/,/^Station/p' | grep -E 'tx packets|tx retries|tx failed' | awk '{print \$3}'" 2>/dev/null | tr '\n' ' '
}
echo "=== preflight ==="; bash /tmp/preflight.sh 2>&1 | tail -n 1
echo "=== AP 计数(前) ==="; apstat; echo
echo "=== ping 30s ==="
ping -I $IF -c 150 -i 0.2 -W 1 $AP 2>&1 | tail -n 2
echo "=== AP 计数(后) ==="; apstat; echo
echo "=== link ==="; /sbin/iw dev $IF link 2>/dev/null | grep -E 'signal|bitrate' | head -n 3
echo "=== USB 新事件 ==="; dmesg | tail -n 20 | grep -iE 'usb.*disconnect|reset high|mt7921.*timeout' || echo none
echo STABILITY2_DONE
