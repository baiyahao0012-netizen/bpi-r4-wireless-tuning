cd /root/merge
echo "=== SDK tar: kernel source presence ==="
tar -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -E "linux-6\.6|build_dir" | head -30
echo "=== SDK tar: top dirs ==="
tar -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | awk -F/ "{print \$2}" | sort -u | head -40
echo "=== SDK tar: any patches dir ==="
tar -tf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" 2>/dev/null | grep -iE "patch" | head -20
echo DONE