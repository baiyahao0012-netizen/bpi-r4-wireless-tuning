set -e
cd /root/merge
rm -rf rootfs_ours
unsquashfs -d rootfs_ours ours_fit/6-rootfs-1.bin > /tmp/unsq2.log 2>&1 && echo UNSQUASH_OK || (echo FAIL; tail -5 /tmp/unsq2.log)
echo "=== ours: release ==="
cat rootfs_ours/etc/openwrt_release
echo "=== ours file count ==="
find rootfs_ours -type f -o -type l | sed "s|^rootfs_ours||" | sort > /root/merge/ours_filelist.txt
wc -l /root/merge/ours_filelist.txt /root/merge/other_filelist.txt
echo "=== files ONLY in other ==="
comm -13 /root/merge/ours_filelist.txt /root/merge/other_filelist.txt > /root/merge/only_other.txt; wc -l < /root/merge/only_other.txt; cat /root/merge/only_other.txt
echo "=== files ONLY in ours ==="
comm -23 /root/merge/ours_filelist.txt /root/merge/other_filelist.txt > /root/merge/only_ours.txt; wc -l < /root/merge/only_ours.txt; head -80 /root/merge/only_ours.txt
echo "=== rtc modules ours ==="
ls rootfs_ours/lib/modules/*/ | grep -i rtc; cat rootfs_ours/etc/modules.d/rtc-pcf8563 2>/dev/null || echo "no modules.d/rtc-pcf8563 in ours"
echo DONE