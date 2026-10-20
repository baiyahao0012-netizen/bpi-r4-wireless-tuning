#!/bin/bash
KO=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt7996/mt7996e.ko
echo "=== objdump -r: relocations involving agg_win_cap ==="
objdump -r "$KO" 2>/dev/null | grep -i agg_win_cap || echo "(no relocs)"
echo ""
echo "=== objdump -R: dynamic relocs ==="
objdump -R "$KO" 2>/dev/null | grep -i agg_win_cap || echo "(no dynamic relocs)"
echo ""
echo "=== nm: ALL symbols (grep agg_win or fops_agg) ==="
nm "$KO" 2>/dev/null | grep -iE 'agg_win|fops_agg'
echo ""
echo "=== size of fops_agg_win_cap from nm ==="
nm -S "$KO" 2>/dev/null | grep fops_agg_win_cap
echo ""
echo "=== CONCLUSION: fops_agg_win_cap definition IS in .rodata ==="
echo "But what does it contain? Let's look at the actual bytes at 0x1ca8"
echo ""
echo "=== hexdump of .rodata around 0x1ca8 ==="
objdump -s -j .rodata "$KO" 2>/dev/null | awk '/Contents of section/,0' | head -30
echo "..."
objdump -s -j .rodata "$KO" 2>/dev/null | grep -A50 '1ca8:' | head -60
