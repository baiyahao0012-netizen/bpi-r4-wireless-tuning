#!/bin/bash
TREE=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6
echo "=== callers of mt7996_mcu_add_tx_ba ==="
grep -rn 'mt7996_mcu_add_tx_ba' "$TREE/mt7996/" 
echo ""
echo "=== ampdu_action / tx_ba handling ==="
grep -rn 'ampdu_action\|AMPDU_TX_START\|mt7996_sta_add.*ba\|add_tx_ba\|ieee80211_start_tx_ba' "$TREE/mt7996/" | head -20
echo ""
echo "=== mac80211 ops ampdu in mt7996 ==="
grep -n -A2 'ampdu_action' "$TREE/mt7996/init.c" "$TREE/mt7996/main.c" 2>/dev/null | head -20
