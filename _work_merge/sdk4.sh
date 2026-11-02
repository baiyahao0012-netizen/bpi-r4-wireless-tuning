echo "=== SDK dl/ contents ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -E "^[^/]+/dl/" | head -30
echo "=== SDK package/kernel ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -E "^[^/]+/package/" | sed "s|^[^/]*/package/||" | awk -F/ "{print \$1\"/\"\$2}" | sort -u | head -40
echo "=== SDK package/kernel/mac80211 ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep "package/kernel/mac80211" | head -20
echo "=== SDK build_dir top ==="
tar --zstd -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep "build_dir/target-aarch64_cortex-a53_musl/" | sed "s|.*target-aarch64_cortex-a53_musl/||" | awk -F/ "{print \$1}" | sort -u | head -20
echo DONE