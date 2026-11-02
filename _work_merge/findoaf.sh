#!/bin/bash
echo "=== A. WSL buildroot ==="
find /root/src -iname "*oaf*" 2>/dev/null | head -20
echo "=== B. SDK ==="
find /root/sdk -iname "*oaf*" 2>/dev/null | head -20
echo "=== C. WSL home / root ==="
find /root -maxdepth 3 -iname "*oaf*" 2>/dev/null | head -20
echo "=== D. board /root and / ==="
ssh -o StrictHostKeyChecking=no root@192.168.240.1 'find / -iname "*oaf*" -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null | head -40' 2>/dev/null
echo "=== E. Windows workspace ==="
find "/mnt/d/Desktop/AI 辅助对话" -iname "*oaf*" 2>/dev/null | head -30
echo DONE
