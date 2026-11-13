#!/bin/bash
cd /tmp/l0
for f in t7a t7b t7c; do
  echo "=== $f feedback/nack/rtx 相关行 ==="
  grep -inE 'nack|retrans|rtx|feedback|psfb|rtpfb|pli|lost' "$f.recv.err" | head -10
done
