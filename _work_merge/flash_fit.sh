#!/bin/sh
TARGET=/tmp/new.itb
echo "=== PRE ==="
ls -la $TARGET
md5sum $TARGET
sync
echo "=== WRITE to /dev/mmcblk0p7 (bs=4096 count=4146) ==="
dd if=$TARGET of=/dev/mmcblk0p7 bs=4096 count=4146 conv=fsync 2>&1
echo "dd rc=$?"
sync
sleep 1
echo "=== READBACK verify ==="
dd if=/dev/mmcblk0p7 bs=4096 count=4146 2>/dev/null | md5sum
echo "EXPECT: $(md5sum $TARGET | cut -d' ' -f1)"
echo "=== partition table unchanged ==="
cat /proc/partitions
echo "=== REBOOT in 3s ==="
sleep 3
reboot
