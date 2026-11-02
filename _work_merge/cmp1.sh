cd /root/merge
echo "=== our .ko vermagic (from backup_sem) ==="
for f in /mnt/d/Desktop/AI*/_work_merge/our_side/backup_sem/modules/*.ko /mnt/d/Desktop/AI*/_work_merge/our_side/backup_sem/oaf.ko; do
  echo "--- $(basename $f)"; strings -a "$f" | grep -E "^vermagic=|^6\.6\.[0-9]+" | head -3; strings -a "$f" | grep -oE "vermagic=[^ ]*" | head -2;
done
echo "=== other rootfs modules ==="
ls rootfs_other/lib/modules/ 2>/dev/null
find rootfs_other/lib/modules -name "*.ko" | head -40
echo "=== other rootfs fstab / overlay ==="
cat rootfs_other/etc/fstab 2>/dev/null
echo "--- init.d/boot overlay bits ---"
grep -n -i -E "overlay|rootfs_data|fit0|loop" rootfs_other/etc/init.d/boot rootfs_other/lib/preinit/* 2>/dev/null | head -30
echo "=== other rootfs: rtc/hwclock related ==="
grep -rl -i "pcf8563\|hwclock" rootfs_other/etc rootfs_other/lib 2>/dev/null | head -20
ls -la rootfs_other/sbin | head -40
echo DONE