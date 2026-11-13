#!/bin/bash
# Route all traffic sourced from Pi wlan1 .126 through wlan1, not eth0.
# Run as root on the Pi: sudo bash setup_media_route.sh
set -e
ip rule add from 192.168.240.126 lookup 100 2>/dev/null || true
ip route replace 192.168.240.0/24 dev wlan1 src 192.168.240.126 table 100
echo "rule:"
ip rule show
echo "table 100:"
ip route show table 100
echo "route get:"
ip route get 192.168.240.1 from 192.168.240.126
