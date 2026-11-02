#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "=== raw dmesg lines ==="
dmesg | grep "section size" | head -12
echo "=== module names (awk) ==="
dmesg | grep "section size" | awk -F"module " "{print \$2}" | awk -F":" "{print \$1}" | sort -u
echo "=== are they loaded? ==="
for m in oaf nfnetlink compat; do
  grep -q "^$m " /proc/modules && echo "$m: LOADED" || echo "$m: not loaded"
done
echo "=== lsmod count ==="
wc -l < /proc/modules
' 2>/dev/null
