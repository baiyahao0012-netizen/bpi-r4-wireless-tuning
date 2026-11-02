#!/bin/bash
cd "/mnt/d/Desktop/AI 辅助对话/_work_merge" || exit 1
echo "=== special files in other_overlay ==="
find other_overlay -type l 2>/dev/null | head -10
find other_overlay -type s 2>/dev/null | head -10
find other_overlay -type p 2>/dev/null | head -10
echo "=== count ==="
find other_overlay -type l 2>/dev/null | wc -l
echo "=== tar other_overlay ==="
tar -czf other_overlay.tar.gz --exclude='*.sock' other_overlay 2>&1 | tail -3
echo "tar rc=$?"
echo "=== tar our_side ==="
tar -czf our_side.tar.gz our_side 2>&1 | tail -3
echo "tar rc=$?"
ls -la other_overlay.tar.gz our_side.tar.gz
echo DONE
