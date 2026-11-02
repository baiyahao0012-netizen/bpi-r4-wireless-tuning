#!/bin/bash
cd /root/fitparts
echo "local size: $(stat -c %s new.itb)"
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cat > /tmp/new.itb' < new.itb
echo "ssh rc=$?"
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'ls -la /tmp/new.itb; md5sum /tmp/new.itb'
echo "local md5: $(md5sum new.itb | cut -d\  -f1)"
