#!/bin/bash
cd /tmp/l0
for f in t7a t7b t7c; do
  echo "=== $f recv.err ==="
  tail -25 "$f.recv.err" 2>/dev/null
  echo "=== $f send.err ==="
  tail -15 "$f.send.err" 2>/dev/null
done
