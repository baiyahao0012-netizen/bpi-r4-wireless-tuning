#!/bin/bash
echo "=== find dscp files ==="
find /root -maxdepth 5 -iname "*dscp*" 2>/dev/null | head -20
echo "=== find in workspace ==="
find "/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src" -iname "*dscp*" 2>/dev/null | head
echo "=== other_src tree ==="
ls -la "/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src/" 2>/dev/null
echo "=== min kernel build ==="
tail -6 /root/kbuild_min_out.log 2>/dev/null
echo "=== /root/merge/sdcard.img info ==="
ls -la /root/merge/sdcard.img 2>/dev/null
file /root/merge/sdcard.img 2>/dev/null
echo "=== /root/merge/rootfs_ours ==="
ls /root/merge/rootfs_ours 2>/dev/null | head
du -sh /root/merge/rootfs_ours 2>/dev/null
echo DONE
