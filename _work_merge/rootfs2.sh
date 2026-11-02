cd /root/merge
echo "=== top-level ==="
ls -la rootfs_other
echo "=== /root ==="
ls -la rootfs_other/root 2>/dev/null
echo "=== /etc/config ==="
ls -la rootfs_other/etc/config
echo "=== /usr/bin ==="
ls -la rootfs_other/usr/bin | head -80
echo "=== filelist ==="
find rootfs_other -type f -o -type l | sed "s|^rootfs_other||" | sort > /root/merge/other_filelist.txt
wc -l /root/merge/other_filelist.txt
head -120 /root/merge/other_filelist.txt
echo DONE