#!/bin/bash
KO=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt7996/mt7996e.ko
echo "=== nm: find t/text symbols ==="
nm "$KO" | grep -E ' agg_win_cap| fops_agg' | head -20
echo ""
echo "=== nm: all text symbols (t/T) ==="
nm "$KO" | grep -E '^[0-9a-f]+ [tT] ' | grep -i agg
echo "(none if no agg_win_cap in text)"
echo ""
echo "=== nm: all rodata symbols (r/R) ==="
nm "$KO" | grep -E '^[0-9a-f]+ [rR] ' | grep agg
echo ""
echo "=== objdump -d: search agg_win_cap ==="
objdump -d "$KO" 2>/dev/null | grep -B2 -A5 'agg_win_cap' | head -40
echo ""
echo "=== objdump -s .rodata ==="
objdump -s -j .rodata "$KO" 2>/dev/null | grep -B1 -A2 'agg_win_cap' | head -30
