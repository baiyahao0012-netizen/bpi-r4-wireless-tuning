#!/bin/bash
cd /tmp/l0
for f in t7a t7b t7c; do
  echo "=== $f send.err nack/retransmit/history ==="
  grep -inE 'nack|retrans|history|rtx|feedback|psfb|rtpfb' "$f.send.err" | head -15
  echo "--- send.err 行数 ---"; wc -l "$f.send.err"
done
