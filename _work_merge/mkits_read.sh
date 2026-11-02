#!/bin/bash
BR=/root/src/openwrt-24.10.0
echo "=== mkits.sh ==="
cat $BR/scripts/mkits.sh
echo "=== min kernel build progress ==="
tail -20 /root/kbuild_min_out.log 2>/dev/null
tail -3 /root/kbuild_min.log 2>/dev/null
echo DONE
