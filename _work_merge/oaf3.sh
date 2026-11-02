#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== /root listing ==="
ls -la /root/ | head -30
echo "=== oaf_start.sh ==="
head -40 /root/oaf_start.sh 2>&1
' 2>/dev/null
