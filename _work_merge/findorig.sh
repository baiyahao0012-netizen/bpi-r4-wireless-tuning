#!/bin/bash
echo "=== /root/fitparts ==="
ls -la /root/fitparts/ 2>&1
echo "=== /root/merge ==="
ls -la /root/merge/ 2>&1 | head
echo "=== /root p7 ==="
ls -la /root/p7.img /root/*.itb /root/*.img 2>&1 | head
echo "=== recover dir ==="
ls -la /root/../../mnt/d/Desktop/AI*/ 2>/dev/null | head -3
echo "=== extract-ikconfig exists? ==="
ls -la /root/kbuild/linux-6.6.73/scripts/extract-ikconfig
echo DONE
