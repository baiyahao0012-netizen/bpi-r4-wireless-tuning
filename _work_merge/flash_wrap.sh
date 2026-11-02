#!/bin/bash
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'sh -s' < /root/flash_board.sh
echo "ssh rc=$?"
