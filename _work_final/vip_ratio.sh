#!/bin/sh
# usage: vip_ratio.sh <2|4|off> [normal_sta_ip]
# 2:1 -> normal 12 MB/s ; 4:1 -> normal 9 MB/s
set -e
RATIO="$1"
IP="$2"
nft delete table ip vipq 2>/dev/null || true
[ "$RATIO" = "off" ] && exit 0
[ -z "$IP" ] && { echo "usage: $0 <2|4|off> <normal_sta_ip>"; exit 1; }
case "$RATIO" in
  2) RATE=12 ;;
  4) RATE=9 ;;
  *) echo "ratio must be 2, 4 or off"; exit 1 ;;
esac
nft add table ip vipq
nft add chain ip vipq out '{ type filter hook output priority 0; }'
nft add rule ip vipq out ip daddr "$IP" limit rate ${RATE} mbytes/second accept
nft add rule ip vipq out ip daddr "$IP" drop
nft list table ip vipq
