#!/bin/bash
cd /tmp/l0
echo "=== recv.err 前 30 行 ==="
sed -n '1,30p' t7d.recv.err
echo "=== recv.err 250,287 行 ==="
sed -n '250,287p' t7d.recv.err
echo "=== send.err 全文 ==="
cat t7d.send.err
