#!/bin/sh
TARGET=/tmp/new.itb
echo "=== PRE ==="
ls -la $TARGET
md5sum $TARGET
sync
echo "=== WRITE p7 bs=4096 count=4146 (only FIT region) ==="
dd if=$TARGET of=/dev/mmcblk0p7 bs=4096 count=4146
echo "dd rc=$?"
sync
sleep 1
echo "=== READBACK ==="
dd if=/dev/mmcblk0p7 bs=4096 count=4146 2>/dev/null | md5sum
echo "EXPECT: $(md5sum $TARGET | cut -d' ' -f1)"
echo "=== partitions ==="
grep -E "fit|mmcblk0p7" /proc/partitions
echo FLASH_DONE
