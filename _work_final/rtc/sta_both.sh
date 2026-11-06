#!/bin/sh
echo "=== 2.4G stations ==="
iw dev phy0.0-ap0 station dump | grep -E "^Station|signal:|tx bitrate:|rx bitrate:" | head -10
echo "=== 5G stations ==="
iw dev phy0.1-ap0 station dump | grep -E "^Station" | head -6
echo "=== leases ==="
grep -E "192.168.240" /tmp/dhcp.leases | awk '{print $3, $4}'
