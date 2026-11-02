cd /root/merge/pristine/backports-6.12.6
P="/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src/354-wifi-mac80211-add-dscp-latency-tracepoint.patch"
echo "=== DRY RUN patch -p1 ==="
patch -p1 --dry-run < "$P" 2>&1 | head -60
echo "=== exit=$? ==="
echo "=== DRY RUN with fuzz ==="
patch -p1 --dry-run -F 3 < "$P" 2>&1 | tail -30
echo DONE