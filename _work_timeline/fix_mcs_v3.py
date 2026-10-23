#!/usr/bin/env python3
BASE = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6'
MCU_C = BASE + "/mt76_connac_mcu.c"
DEBUGFS_C = BASE + "/debugfs.c"

# 1. mt76_connac_mcu.c: define variable + EXPORT
with open(MCU_C) as f:
    c = f.read()
# remove extern if present
c = c.replace("extern u8 mt76_force_mcs;\n", "")
# add definition after includes
if "u8 mt76_force_mcs = 0xFF;" not in c:
    lines = c.split("\n")
    for i, l in enumerate(lines):
        if l.startswith("#include"):
            li = i
    lines.insert(li+1, "/* MCS force lock: 0-7 = force MCS, 0xFF = auto */")
    lines.insert(li+2, "u8 mt76_force_mcs = 0xFF;")
    lines.insert(li+3, "EXPORT_SYMBOL_GPL(mt76_force_mcs);")
    c = "\n".join(lines)
with open(MCU_C, "w") as f:
    f.write(c)
print("[+] connac_mcu: variable defined + exported")

# 2. debugfs.c: extern only (no definition)
with open(DEBUGFS_C) as f:
    d = f.read()
# remove the definition we added
d = d.replace("/* MCS force lock: 0-7 = force MCS, 0xFF = auto */\nu8 mt76_force_mcs = 0xFF;\n", "")
# ensure extern exists
if "extern u8 mt76_force_mcs;" not in d:
    lines = d.split("\n")
    for i, l in enumerate(lines):
        if "#include \"mt76.h\"" in l:
            lines.insert(i+1, "extern u8 mt76_force_mcs;")
            break
    d = "\n".join(lines)
with open(DEBUGFS_C, "w") as f:
    f.write(d)
print("[+] debugfs: extern only")
print("DONE")
