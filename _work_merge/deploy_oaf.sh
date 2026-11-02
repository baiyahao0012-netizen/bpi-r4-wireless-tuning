#!/bin/bash
B=192.168.240.1
SSH="ssh -o StrictHostKeyChecking=no root@$B"
echo '=== backup old ==='
$SSH 'cp -n /root/oaf.ko /root/oaf.ko.orig-0x280; ls -la /root/oaf.ko*' 2>/dev/null
echo '=== deploy ==='
$SSH 'cat > /root/oaf.ko.new' < /root/oafbuild/oaf.ko
$SSH 'md5sum /root/oaf.ko.new' 2>/dev/null
echo DONE1
