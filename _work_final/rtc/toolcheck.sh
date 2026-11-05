#!/bin/sh
for t in python3 python nc ncat socat perl awk gcc; do
  p=$(command -v $t 2>/dev/null)
  if [ -n "$p" ]; then echo "$t -> $p"; else echo "$t -> none"; fi
done
echo "--- python3 ---"
python3 -V 2>&1 | head -1
