cd "/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src"
echo "=== sha256 of key artifacts ==="
sha256sum 354-wifi-mac80211-add-dscp-latency-tracepoint.patch 355-wifi-mt76-mt7996-report-tx-retries.patch dscpstats dscpstats.awk README.md REQUIREMENTS.md
echo "=== backports reference tree markers ==="
grep -n "BACKPORTS_VERSION\|BACKPORTED_KERNEL_VERSION" backports-6.12.96/versions 2>/dev/null | head
echo "=== 354 hunk count ==="
grep -c "^@@" 354-wifi-mac80211-add-dscp-latency-tracepoint.patch
echo "=== trace.h tail of reference tree ==="
tail -60 backports-6.12.96/net/mac80211/trace.h
echo DONE