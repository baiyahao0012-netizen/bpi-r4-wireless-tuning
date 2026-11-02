cd /root/merge
mkdir -p ovl
mountpoint -q ovl || mount -t f2fs -o ro,loop overlay.img ovl 2>&1 || echo MOUNT_ERR
DST="/mnt/d/Desktop/AI 辅助对话/_work_merge/other_overlay"
rm -rf "$DST"; mkdir -p "$DST"
cp -a ovl/upper/. "$DST/" && echo COPY_OK
chmod -R u+rwX "$DST" 2>/dev/null || true
find "$DST" -type f | wc -l
echo "=== /root/reload.sh ==="
cat ovl/upper/root/reload.sh
echo "=== /root/dscpstats.awk ==="
cat ovl/upper/root/dscpstats.awk
echo "=== /etc/config/wireless ==="
cat ovl/upper/etc/config/wireless
echo "=== /etc/config/network ==="
cat ovl/upper/etc/config/network
echo "=== /etc/config/system ==="
cat ovl/upper/etc/config/system
echo "=== /etc/config/firewall ==="
cat ovl/upper/etc/config/firewall
echo DONE