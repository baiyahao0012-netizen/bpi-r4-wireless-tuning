#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
echo "--- ps ---"
ps | grep -E "[c]opymods|[c]p -f"
echo "--- pid fds ---"
for p in $(pgrep copymods) $(pgrep -f "cp -f"); do
  echo "pid=$p"
  ls -l /proc/$p/fd 2>/dev/null | head -5
  cat /proc/$p/wchan 2>/dev/null; echo
done
echo "--- log ---"
cat /tmp/copymods.log 2>&1
echo "--- dmesg tail ---"
dmesg | tail -12
echo "--- df /overlay ---"
df -h /overlay
' 2>/dev/null
