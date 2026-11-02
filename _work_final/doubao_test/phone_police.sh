#!/bin/sh
# phone_police.sh <kbytes_per_sec> <baseline|accel>
PHONE=192.168.240.219
RATE=${1:-128}
MODE=${2:-baseline}
nft delete table ip phone_police 2>/dev/null
nft add table ip phone_police
nft add chain ip phone_police post '{ type filter hook postrouting priority -149; }'
if [ "$MODE" = "accel" ]; then
  nft add rule ip phone_police post ip daddr $PHONE ct mark and 0xffff == 0x76c counter accept
fi
nft add rule ip phone_police post ip daddr $PHONE limit rate ${RATE} kbytes/second counter accept
nft add rule ip phone_police post ip daddr $PHONE counter drop
echo "mode=$MODE rate=${RATE}KB/s"
nft -s list table ip phone_police
