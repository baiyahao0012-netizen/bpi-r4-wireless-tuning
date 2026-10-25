#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6

# Move tools away
mv "$BD/tools" "$BD/tools.bak" 2>/dev/null

# Force recompile our changed files
rm -f "$BD/mt76_connac_mcu.o" "$BD/debugfs.o" "$BD/.mt76_connac_mcu.o.cmd" "$BD/.debugfs.o.cmd"

cd "$SDK"
make package/kernel/mt76/compile V=s -j24 2>&1 | grep -E "CC|LD|Error|error|mt76_force" | head -20

# Restore tools
mv "$BD/tools.bak" "$BD/tools" 2>/dev/null

echo "=== ko files ==="
ls -la --time-style=+%H:%M "$BD"/*.ko | grep -E "mt76\.ko|connac-lib"
