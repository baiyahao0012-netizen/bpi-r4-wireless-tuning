cd /root/merge
OTH="/mnt/d/Desktop/AI 辅助对话/_work_merge/other_overlay"
echo "=== their dscpstats binary strings ==="
strings -a "$OTH/root/dscpstats" | head -60
echo "=== their /etc/board.json ==="
cat "$OTH/etc/board.json"
echo "=== their wireless backups (diff) ==="
for f in "$OTH"/root/wireless.bak-*; do echo "--- $f"; cat "$f"; done
echo "=== their dscpstats head ==="
head -5 "$OTH/root/dscpstats"
echo DONE