#!/bin/bash
echo "=== min kernel build tail ==="
tail -25 /root/kbuild_min_out.log 2>/dev/null
echo "=== build log tail ==="
tail -5 /root/kbuild_min.log 2>/dev/null
echo "=== dscpstats tool ==="
ls -la /root/merge/other_src/ 2>/dev/null || ls -la "/root/merge/" 2>/dev/null
find /root -maxdepth 3 -name "dscpstats*" 2>/dev/null
echo "=== dscpstats content ==="
for f in $(find /root -maxdepth 3 -name "dscpstats" -o -maxdepth 3 -name "dscpstats.awk" 2>/dev/null); do
  echo "--- $f ---"; head -50 "$f"
done
echo DONE
