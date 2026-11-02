cd /root/merge
echo "=== what is under linux-6.6.73 (top-level dirs) ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep "linux-6.6.73/" | sed "s|.*/linux-6.6.73/||" | awk -F/ "{print \$1}" | sort | uniq -c | sort -rn | head -30
echo "=== mac80211 present? ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -c "net/mac80211"
echo "=== mt76 present? ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -c "mediatek/mt76"
echo "=== does SDK have kernel source tarball/dl? ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -E "dl/|linux-6.6.73.tar|\.tar\.xz" | head -20
echo DONE