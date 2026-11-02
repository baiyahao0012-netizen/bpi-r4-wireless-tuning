#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== find oaf.ko ==="
find / -name "oaf*.ko" -not -path "/proc/*" 2>/dev/null
echo "=== /lib/modules dirs ==="
ls /lib/modules/
echo "=== opkg oaf ==="
opkg list-installed 2>/dev/null | grep -i oaf
echo "=== oaf related files ==="
ls -la /etc/modules.d/ | grep -i oaf
ls -la /etc/init.d/ | grep -i oaf
find / -name "*oaf*" -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null | head -20
' 2>/dev/null
