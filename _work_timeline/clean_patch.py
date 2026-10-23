#!/usr/bin/env python3
"""Clean patch: add force_mcs debugfs node and sta_tlv override.
Start from pristine source, minimal changes only."""

base = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/'

# === 1. Patch debugfs.c ===
db_path = base + 'debugfs.c'
with open(db_path, 'r') as f:
    lines = f.readlines()

# Insert global var + fops after #include "mt76.h"
for i, l in enumerate(lines):
    if '#include "mt76.h"' in l:
        insert = '''
/* MCS force lock: 0-7 = force MCS, 0xFF = auto */
u8 mt76_force_mcs = 0xFF;
EXPORT_SYMBOL_GPL(mt76_force_mcs);

static int force_mcs_show(void *data, u64 *val)
{
	*val = mt76_force_mcs;
	return 0;
}

static int force_mcs_write(void *data, u64 val)
{
	if (val > 0xFF)
		return -EINVAL;
	mt76_force_mcs = (u8)val;
	return 0;
}

DEFINE_DEBUGFS_ATTRIBUTE(force_mcs_fops, force_mcs_show, force_mcs_write, "%llu\\n");
'''
        lines.insert(i+1, insert)
        print(f'debugfs.c: inserted global+fops after line {i+1}')
        break

# Add debugfs_create_file after otp blob
for i, l in enumerate(lines):
    if 'debugfs_create_blob("otp"' in l:
        lines.insert(i+1, '\tdebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);\n')
        print(f'debugfs.c: added force_mcs file after otp at line {i+1}')
        break

with open(db_path, 'w') as f:
    f.writelines(lines)

# === 2. Patch mt76_connac_mcu.c ===
cu_path = base + 'mt76_connac_mcu.c'
with open(cu_path, 'r') as f:
    lines = f.readlines()

# Find last #include line, add extern after it
last_include = -1
for i, l in enumerate(lines):
    if l.startswith('#include'):
        last_include = i
lines.insert(last_include + 1, 'extern u8 mt76_force_mcs;\n')
print(f'connac_mcu.c: added extern after line {last_include+1}')

# Find sta_tlv: memcpy(rx_mcs_bitmask) and add override after it
for i, l in enumerate(lines):
    if 'memcpy(ra_info->rx_mcs_bitmask' in l:
        # Insert override after this line (and the closing parenthesis line if any)
        # The memcpy line ends with ), so insert after it
        override = '''
	if (mt76_force_mcs < 8) {
		memset(ra_info->rx_mcs_bitmask, 0, HT_MCS_MASK_NUM);
		ra_info->rx_mcs_bitmask[mt76_force_mcs] = 0xff;
		printk("mt76: FORCE MCS%u\\n", mt76_force_mcs);
	}
'''
        lines.insert(i+1, override)
        print(f'connac_mcu.c: added override after memcpy at line {i+1}')
        break

with open(cu_path, 'w') as f:
    f.writelines(lines)

print('All patched!')
