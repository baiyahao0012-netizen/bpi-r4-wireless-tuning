#!/bin/bash
echo "=== LOCAL ==="
cd /root/modstage/lib/modules/6.6.73
md5sum *.ko | sort -k2 > /root/local_md5.txt
wc -l < /root/local_md5.txt
echo "=== BOARD UPPER ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'cd /overlay/upper/lib/modules/6.6.73 && md5sum *.ko | sort -k2' 2>/dev/null > /root/board_upper_md5.txt
wc -l < /root/board_upper_md5.txt
echo "=== DIFF (local vs board upper) ==="
diff /root/local_md5.txt /root/board_upper_md5.txt && echo "IDENTICAL - all 103 match" || echo "^^ differences above"
echo DONE
