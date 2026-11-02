SDK="/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst"
echo "=== total entries ==="
tar --zstd -tf "$SDK" 2>/dev/null | wc -l
echo "=== top level ==="
tar --zstd -tf "$SDK" 2>/dev/null | sed "s|^[^/]*/||" | awk -F/ "NF>1{print \$1}" | sort | uniq -c | sort -rn | head -25
echo "=== staging_dir ==="
tar --zstd -tf "$SDK" 2>/dev/null | grep -oE "staging_dir/[^/]+/" | sort -u | head -20
echo "=== target/linux/mediatek files ==="
tar --zstd -tf "$SDK" 2>/dev/null | grep "target/linux/mediatek" | head -20
echo "=== any .config / config.buildinfo ==="
tar --zstd -tf "$SDK" 2>/dev/null | grep -iE "config.buildinfo|\.config$" | head -10
echo "=== bin/ ==="
tar --zstd -tf "$SDK" 2>/dev/null | grep -E "^[^/]+/bin/" | head -10
echo "=== feeds ==="
tar --zstd -tf "$SDK" 2>/dev/null | grep -E "^[^/]+/feeds" | head -10
echo "=== mac80211 / mt76 anywhere ==="
tar --zstd -tf "$SDK" 2>/dev/null | grep -iE "mac80211|mt76" | head -20
echo DONE