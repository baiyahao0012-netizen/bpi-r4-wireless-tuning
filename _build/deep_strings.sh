#!/bin/bash
KO=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt7996/mt7996e.ko
echo "=== ALL strings with agg_win_cap ==="
strings "$KO" | grep -i agg_win_cap
echo ""
echo "=== ALL strings with mt7996 ==="
strings "$KO" | grep -c mt7996
echo ""
echo "=== ALL strings with fops_ ==="
strings "$KO" | grep fops | head -10
echo ""
echo "=== nm agg_win_cap ==="
nm "$KO" 2>/dev/null | grep agg_win_cap || echo "nm not available or stripped"
echo ""
echo "=== objdump agg_win_cap ==="
objdump -t "$KO" 2>/dev/null | grep agg_win_cap || echo "objdump failed"
echo ""
echo "=== test: is read/write STRING literally in .ko? ==="
grep -c 'agg_win_cap_read' "$KO" || echo "0 matches (binary grep)"
grep -c 'agg_win_cap_write' "$KO" || echo "0 matches (binary grep)"
grep -c 'buf_size clamped' "$KO" || echo "0 matches (binary grep)"
