#!/bin/bash
mkdir -p /root/.ssh
cp -f /mnt/c/Users/15732/.ssh/id_ed25519_github_elf2 /root/.ssh/ 2>/dev/null
cp -f /mnt/c/Users/15732/.ssh/known_hosts /root/.ssh/ 2>/dev/null
chmod 700 /root/.ssh
chmod 600 /root/.ssh/id_ed25519_github_elf2 2>/dev/null
echo "=== test wsl ssh ==="
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 root@192.168.240.1 "echo WSL_SSH_OK; cat /etc/openwrt_release | head -3" 2>&1 | head -10
echo SETUP_DONE
