#!/bin/bash
A="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1"
echo "=== classes ==="
$A 'tc -s class show dev phy0.1-ap0 | grep -E "class htb|Sent"'
echo "=== filters ==="
$A 'tc filter show dev phy0.1-ap0 | head -n 8'
