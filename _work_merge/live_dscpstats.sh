#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
cd /tmp/dscptest/dscptest
echo "=== start ==="
./dscpstats start 2>&1
echo "=== nft mark: icmp->af41(0x88), udp 9999->cs1(0x20) ==="
nft add table inet dsctest 2>/dev/null
nft add chain inet dsctest out "{ type route hook output priority mangle; }" 2>/dev/null
nft add rule inet dsctest out ip protocol icmp ip dscp set af41 2>/dev/null
nft add rule inet dsctest out udp dport 9999 ip dscp set cs1 2>/dev/null
echo "=== generate traffic ==="
ping -c 40 -W 1 192.168.3.1 >/dev/null 2>&1 &
# UDP burst marked CS1 to the gateway
( for i in $(seq 1 30); do echo "hello-$i" | nc -u -w 0 192.168.3.1 9999 2>/dev/null; done ) &
wait
sleep 2
echo "=== status ==="
./dscpstats status 2>&1
echo "=== stop ==="
./dscpstats stop 2>&1
nft delete table inet dsctest 2>/dev/null
' 2>&1 | grep -v "WARNING|post-quantum|store now|upgraded|openssh.com"
