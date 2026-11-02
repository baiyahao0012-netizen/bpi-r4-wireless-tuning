#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'grep oaf /proc/modules; echo ---; cat /proc/sys/fwx/appfilter_enable; echo ---; cat /proc/sys/fwx/version 2>/dev/null' 2>&1 | grep -v "WARNING\|post-quantum\|store now\|upgraded\|openssh.com"
echo DONE6
