#!/bin/bash
echo "=== transfer ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'rm -rf /tmp/dscptest; mkdir -p /tmp/dscptest; cd /tmp/dscptest && tar xzf -' < /root/dscptest.tar.gz
echo "rc=$?"
echo "=== run tests on board ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cd /tmp/dscptest && chmod +x dscpstats test/*.sh && sh test/run_tests.sh 2>&1 | tail -30' 2>/dev/null
echo DONE
