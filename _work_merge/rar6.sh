cd /root/merge/incoming
DST="/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src"
rm -rf "$DST"; mkdir -p "$DST"
cp -a bsdx/backports-src/. "$DST/" && echo COPY_OK
chmod -R u+rwX "$DST" 2>/dev/null || true
ls -la "$DST"
echo "=== patch 354 head ==="
head -80 "$DST/354-wifi-mac80211-add-dscp-latency-tracepoint.patch"
echo "=== patch 355 full ==="
cat "$DST/355-wifi-mt76-mt7996-report-tx-retries.patch"
echo DONE