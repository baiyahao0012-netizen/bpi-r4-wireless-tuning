#!/bin/bash
KO=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt7996/mt7996e.ko
echo "=== agg_win_cap related strings ==="
strings "$KO" | grep -i agg_win_cap
echo "=== write/read func strings ==="
strings "$KO" | grep -E 'agg_win_cap_write|agg_win_cap_read'
echo "=== printk strings ==="
strings "$KO" | grep -E 'pr_info|pr_err|dev_info' | head -10
