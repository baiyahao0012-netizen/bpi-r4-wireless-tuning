#!/bin/bash
cd "/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src"
rm -rf /root/dscptest; mkdir -p /root/dscptest
cp dscpstats dscpstats.awk README.md /root/dscptest/
cp -r test /root/dscptest/
chmod +x /root/dscptest/dscpstats /root/dscptest/test/*.sh 2>/dev/null
echo "=== files ==="
find /root/dscptest -type f | sort
echo "=== run tests in WSL (gawk) ==="
cd /root/dscptest && sh test/run_tests.sh 2>&1 | tail -25
echo "=== tar for board ==="
cd /root && tar czf /root/dscptest.tar.gz -C /root dscptest
ls -la /root/dscptest.tar.gz
echo DONE
