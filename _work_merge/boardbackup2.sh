#!/bin/bash
OUT="/mnt/d/Desktop/AI 辅助对话/_work_recover"
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@192.168.240.1"
echo "=== config backup via ssh cat ==="
$SSH "cat /tmp/cfg_merge_pre.bak" > "$OUT/cfg_pre_kernelflash_20261102.tar.gz" 2>/dev/null
ls -la "$OUT/cfg_pre_kernelflash_20261102.tar.gz"
echo "=== raw p7 backup (224MB) ==="
date
$SSH "dd if=/dev/mmcblk0p7 bs=4M 2>/dev/null | gzip -1" > "$OUT/p7_raw_pre_kernelflash_20261102.img.gz" 2>/dev/null
echo "dd rc=$?"
date
ls -la "$OUT/p7_raw_pre_kernelflash_20261102.img.gz"
echo "=== verify gzip integrity ==="
gzip -t "$OUT/p7_raw_pre_kernelflash_20261102.img.gz" && echo "GZIP_OK" || echo "GZIP_BAD"
gzip -l "$OUT/p7_raw_pre_kernelflash_20261102.img.gz"
echo BACKUP2_DONE
