#!/usr/bin/env python3
"""MCS force lock patch for mt76 - v1"""
import sys, os

BASE = sys.argv[1]
MCU_C = os.path.join(BASE, "mt76_connac_mcu.c")
DEBUGFS_C = os.path.join(BASE, "debugfs.c")

# === 1. mt76_connac_mcu.c ===
with open(MCU_C, "r", encoding="utf-8") as f:
    c = f.read()

# Add global after first #include block
if "mt76_force_mcs" not in c:
    lines = c.split("\n")
    last_inc = 0
    for i, line in enumerate(lines):
        if line.startswith("#include"):
            last_inc = i
    lines.insert(last_inc + 1, "")
    lines.insert(last_inc + 2, "/* MCS force lock: 0-7 = force MCS, 0xFF = auto */")
    lines.insert(last_inc + 3, "u8 mt76_force_mcs = 0xFF;")
    c = "\n".join(lines)
    print("[+] global mt76_force_mcs added")

# Override rx_mcs_bitmask
old = """	if (sta->deflink.ht_cap.ht_supported)
		memcpy(ra_info->rx_mcs_bitmask,
		       sta->deflink.ht_cap.mcs.rx_mask,
		       HT_MCS_MASK_NUM);"""
new = """	if (sta->deflink.ht_cap.ht_supported) {
		memcpy(ra_info->rx_mcs_bitmask,
		       sta->deflink.ht_cap.mcs.rx_mask,
		       HT_MCS_MASK_NUM);
		if (mt76_force_mcs < 8) {
			memset(ra_info->rx_mcs_bitmask, 0, HT_MCS_MASK_NUM);
			ra_info->rx_mcs_bitmask[mt76_force_mcs] = 0xff;
			printk("mt76: FORCE MCS%u\\n", mt76_force_mcs);
		}
	}"""
if old in c:
    c = c.replace(old, new)
    print("[+] rx_mcs_bitmask override patched")
else:
    print("[!] memcpy pattern NOT found")

with open(MCU_C, "w", encoding="utf-8") as f:
    f.write(c)

# === 2. debugfs.c ===
with open(DEBUGFS_C, "r", encoding="utf-8") as f:
    d = f.read()

if "force_mcs" not in d:
    # Add extern at top
    d = "extern u8 mt76_force_mcs;\n" + d
    # Add debugfs node before return dir
    d = d.replace(
        "\tdebugfs_create_devm_seqfile(dev->dev, \"rx-queues\", dir,",
        '\tdebugfs_create_u8("force_mcs", 0644, dir, &mt76_force_mcs);\n\tdebugfs_create_devm_seqfile(dev->dev, "rx-queues", dir,'
    )
    print("[+] force_mcs debugfs node added")

with open(DEBUGFS_C, "w", encoding="utf-8") as f:
    f.write(d)

print("PATCH_DONE")
