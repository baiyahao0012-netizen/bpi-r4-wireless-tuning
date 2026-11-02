#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== /root/oaf.ko ==="
ls -la /root/oaf.ko 2>&1
echo "=== full /root listing ==="
ls -la /root/ | tail -40
echo "=== oaf source? ==="
find /root -iname "*oaf*" 2>/dev/null
' 2>/dev/null
