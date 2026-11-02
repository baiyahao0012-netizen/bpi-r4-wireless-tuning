cd /root/merge
DST="/mnt/d/Desktop/AI 辅助对话/_work_merge/other_overlay"
mkdir -p "$DST"
cp -a ovl/upper/. "$DST/" 2>&1 | head -5
chmod -R u+rwX "$DST" 2>/dev/null || true
echo "=== copied ==="
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
echo DONE