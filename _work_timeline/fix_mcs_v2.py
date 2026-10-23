#!/usr/bin/env python3
"""Fix MCS patch: move variable to debugfs.c (in mt76.ko) to avoid cross-module symbol issue"""
import os

BASE = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6'
MCU_C = os.path.join(BASE, "mt76_connac_mcu.c")
DEBUGFS_C = os.path.join(BASE, "debugfs.c")

# 1. Remove global + EXPORT from mt76_connac_mcu.c, keep only usage
with open(MCU_C, "r") as f:
    c = f.read()

# Remove the global definition and EXPORT
c = c.replace("/* MCS force lock: 0-7 = force MCS, 0xFF = auto */\nu8 mt76_force_mcs = 0xFF;\nEXPORT_SYMBOL_GPL(mt76_force_mcs);\n", "")
# Add extern declaration instead
if "extern u8 mt76_force_mcs;" not in c:
    # Add after includes
    lines = c.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#include"):
            last_inc = i
    lines.insert(last_inc + 1, "extern u8 mt76_force_mcs;")
    c = "\n".join(lines)

with open(MCU_C, "w") as f:
    f.write(c)
print("[+] mt76_connac_mcu.c: global removed, extern added")

# 2. Define variable in debugfs.c (mt76.ko itself)
with open(DEBUGFS_C, "r") as f:
    d = f.read()

# Remove the extern line (we're defining it now)
d = d.replace("extern u8 mt76_force_mcs;\n", "")
# Add actual definition after includes
if "u8 mt76_force_mcs = 0xFF;" not in d:
    lines = d.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#include"):
            last_inc = i
    lines.insert(last_inc + 1, "/* MCS force lock: 0-7 = force MCS, 0xFF = auto */")
    lines.insert(last_inc + 2, "u8 mt76_force_mcs = 0xFF;")
    d = "\n".join(lines)

with open(DEBUGFS_C, "w") as f:
    f.write(d)
print("[+] debugfs.c: variable defined here")

print("FIX_DONE")
