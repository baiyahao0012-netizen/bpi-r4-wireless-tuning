#!/bin/bash
# Stability probe: preflight + 30 s ping + USB/link error diff.
IF=wlan0
AP=192.168.240.1
echo "=== preflight ==="
bash /tmp/preflight.sh 2>&1 | tail -n 2
echo "=== 起始状态 ==="
/sbin/iw dev $IF link 2>/dev/null | grep -E 'signal|bitrate|freq|SSID' | head -n 4
D0=$(dmesg | wc -l)
echo "=== ping 30s (150 x 0.2s) ==="
ping -I $IF -c 150 -i 0.2 -W 1 $AP 2>&1 | tail -n 3
echo "=== 之后状态 ==="
/sbin/iw dev $IF link 2>/dev/null | grep -E 'signal|bitrate|freq|SSID' | head -n 4
ip -4 -br addr show $IF
echo "=== 接口错误计数 ==="
ip -s link show $IF | tail -n 4
echo "=== 期间新增 USB 事件 ==="
dmesg | tail -n +$((D0+1)) | grep -iE 'usb|mt7921' | tail -n 6 || echo "none"
echo "=== AP 侧该 STA 计数 ==="
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@$AP \
  "iw dev phy0.1-ap0 station dump | sed -n '/90:de:80:1c:6a:7a/,/^Station/p' | grep -E 'signal:|tx failed|tx retries|tx packets' | head -n 5" 2>/dev/null
echo STABILITY_DONE
