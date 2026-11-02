#!/bin/bash
B=192.168.240.1
SSH="ssh -o StrictHostKeyChecking=no root@$B"
$SSH 'echo "--- /etc/init.d/oaf-mini ---"; cat /etc/init.d/oaf-mini; echo; echo "--- /root/oaf_start.sh ---"; cat /root/oaf_start.sh; echo; echo "--- dmesg tail 12 ---"; dmesg | tail -12' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo DONE4
