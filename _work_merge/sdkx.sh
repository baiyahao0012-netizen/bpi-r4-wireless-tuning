cd /root/merge
mkdir -p sdkx
echo "=== extracting net/mac80211 from SDK kernel source ==="
tar --zstd -xf "/mnt/d/Desktop/AI 辅助对话/_sdk/openwrt-sdk.tar.zst" -C sdkx --wildcards "*/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/net/mac80211/*" 2>&1 | head -5
echo "=== find tx.c ==="
find sdkx -name "tx.c" -path "*mac80211*" | head
TX=$(find sdkx -name "tx.c" -path "*mac80211*" | head -1)
echo "TX=$TX"
echo "=== our WDRR markers ==="
grep -n "fq_weight\|wdrr\|WDRR" "$TX" | head -20
echo "=== fq_impl.h / fq.h in sdk? ==="
find sdkx -name "fq_impl.h" -o -name "fq.h" | head
echo DONE