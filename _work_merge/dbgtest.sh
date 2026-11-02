#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 '
cd /tmp/dscptest
echo "=== files ==="
ls -la
echo "=== awk version ==="
awk --version 2>&1 | head -2; busybox awk --help 2>&1 | head -2
echo "=== run L2 directly ==="
sh test/l2_aggregate.sh 2>&1 | tail -20
echo "=== rc=$? ==="
echo "=== run L3 directly ==="
sh test/l3_pipeline.sh 2>&1 | tail -25
' 2>&1 | head -80
