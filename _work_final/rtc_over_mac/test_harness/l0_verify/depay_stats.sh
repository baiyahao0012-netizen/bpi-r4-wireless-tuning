#!/bin/bash
# depay_stats.sh — 统计 depay 调试日志中的 AU/NAL 数量
ERR=/tmp/l0/depay_debug.err
echo "AU_completed=$(grep -c 'taking completed AU' "$ERR")"
echo "FU_output=$(grep -c 'output .* bytes' "$ERR")"
echo "NAL_handled=$(grep -c 'handle NAL type' "$ERR")"
echo "=== NAL 类型分布 ==="
grep -oE 'handle NAL type [0-9]+' "$ERR" | sort | uniq -c
echo "=== 最后 5 个 completed AU 行号 ==="
grep -n 'taking completed AU' "$ERR" | tail -5
echo "=== 最后 10 行 ==="
tail -10 "$ERR"
