#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== /etc/init.d/oaf-mini ==="
cat /etc/init.d/oaf-mini
echo "=== rc.d links ==="
ls -la /etc/rc.d/ | grep -i oaf
echo "=== any oaf in /usr /bin /sbin /root ==="
grep -rl "oaf" /etc/init.d/ /usr/bin/ /usr/sbin/ 2>/dev/null | head
echo "=== insmod oaf verbose ==="
modprobe -v oaf 2>&1
echo "=== modules.dep has oaf? ==="
grep -i oaf /lib/modules/6.6.73/modules.* 2>/dev/null | head
' 2>/dev/null
