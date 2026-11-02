#!/bin/bash
OUT="/mnt/d/Desktop/AI 辅助对话/_work_recover"
mkdir -p "$OUT"
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@192.168.240.1"
echo "=== board identity ==="
$SSH "cat /etc/openwrt_release; echo; cat /proc/partitions" 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
echo "=== sysupgrade config backup ==="
$SSH "sysupgrade -b /tmp/cfg_merge_pre.bak && ls -la /tmp/cfg_merge_pre.bak" 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
scp -o StrictHostKeyChecking=no root@192.168.240.1:/tmp/cfg_merge_pre.bak "$OUT/cfg_pre_kernelflash_20261102.tar.gz" 2>&1 | grep -v "WARNING\|vulnerable\|upgraded"
ls -la "$OUT/cfg_pre_kernelflash_20261102.tar.gz" 2>&1
echo "=== overlay tar ==="
$SSH "tar -C /overlay -czf - . 2>/dev/null" > "$OUT/overlay_pre_kernelflash_20261102.tar.gz"
ls -la "$OUT/overlay_pre_kernelflash_20261102.tar.gz" 2>&1
echo BACKUP_PART1_DONE
