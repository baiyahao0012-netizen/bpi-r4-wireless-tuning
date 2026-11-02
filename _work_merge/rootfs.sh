set -e
cd /root/merge
rm -rf rootfs_other
unsquashfs -d rootfs_other fit/rootfs-1.bin > /tmp/unsq.log 2>&1 && echo UNSQUASH_OK || (echo UNSQUASH_FAIL; tail -5 /tmp/unsq.log)
echo "=== counts ==="
find rootfs_other -type f | wc -l; find rootfs_other -type d | wc -l; du -sh rootfs_other
echo "=== openwrt_release ==="
cat rootfs_other/etc/openwrt_release 2>/dev/null; echo; cat rootfs_other/etc/os-release 2>/dev/null
echo "=== /etc/config/wireless ==="
cat rootfs_other/etc/config/wireless 2>/dev/null
echo "=== top-level ==="
ls -la rootfs_other
echo "=== root home ==="
ls -la rootfs_other/root 2>/dev/null | head -60
echo "=== etc/config ==="
ls -la rootfs_other/etc/config
echo DONE