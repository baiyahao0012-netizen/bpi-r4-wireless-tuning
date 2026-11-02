#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
cd /tmp/dscptest/dscptest
chmod +x dscpstats test/*.sh
echo "=== L2 ==="
sh test/l2_aggregate.sh 2>&1 | tail -20
echo "L2 rc=$?"
echo "=== L3 ==="
sh test/l3_pipeline.sh 2>&1 | tail -25
echo "L3 rc=$?"
' 2>&1 | grep -v "WARNING|post-quantum|store now|upgraded|openssh.com"
