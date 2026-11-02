cd /root/merge/incoming
rm -rf bsdx && mkdir bsdx
bsdtar -xf backports-src.rar -C bsdx 2>&1 | head -5
echo "=== non-empty / empty ==="
find bsdx -type f -size +0 | wc -l; find bsdx -type f -size 0 | wc -l
du -sh bsdx
echo "=== top files ==="
ls -la bsdx/backports-src/
echo "=== mac80211 tracepoint patch exists? ==="
wc -l bsdx/backports-src/354-wifi-mac80211-add-dscp-latency-tracepoint.patch
echo "=== backports tree net/mac80211 present? ==="
ls bsdx/backports-src/backports-6.12.96/net/mac80211/ 2>/dev/null | head -20
ls bsdx/backports-src/backports-6.12.96/net/mac80211/ 2>/dev/null | wc -l
echo DONE