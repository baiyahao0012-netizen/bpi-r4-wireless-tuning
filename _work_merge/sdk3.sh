echo "=== SDK: mac80211-regular / mt76 build dirs ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -oE "linux-mediatek_filogic/[^/]+/" | sort -u
echo "=== SDK: backports version dirs ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -oE "backports-6\.12\.[0-9]+" | sort -u
echo "=== SDK: mt76 version dirs ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -oE "mt76-[0-9]{4}\.[0-9]{2}\.[0-9]{2}[^/]*" | sort -u
echo "=== SDK: does mac80211 source exist under backports? ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -E "mac80211-regular/backports" | head -10
echo "=== SDK: package mac80211 patches dir ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -E "package/kernel/mac80211/" | head -20
echo DONE