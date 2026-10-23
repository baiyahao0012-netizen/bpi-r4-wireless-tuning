#!/usr/bin/env python3
"""Clean debugfs.c: remove all force_mcs related code, then re-add correctly."""

path = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/debugfs.c'

with open(path, 'r') as f:
    lines = f.readlines()

# Remove all lines containing force_mcs
new_lines = []
skip_block = False
for i, l in enumerate(lines):
    if 'force_mcs' in l:
        print(f'skipping line {i+1}: {l.strip()[:60]}')
        # Skip multi-line blocks around force_mcs fops
        if 'DEFINE_DEBUGFS_ATTRIBUTE' in l or 'static int force_mcs' in l or 'static ssize_t force_mcs' in l:
            skip_block = True
        continue
    if skip_block:
        # Skip until we find a blank line or next function
        if l.strip() == '' or l.startswith('static ') or l.startswith('#'):
            skip_block = False
            continue
        continue
    new_lines.append(l)

with open(path, 'w') as f:
    f.writelines(new_lines)

print('Cleaned, now re-adding correct fops...')

# Re-add correct global var + simple_attr fops
with open(path, 'r') as f:
    lines = f.readlines()

# Insert after #include "mt76.h"
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
        print(f'Inserted after line {i+1}')
        break

# Add debugfs_create_file after otp blob
for i, l in enumerate(lines):
    if 'debugfs_create_blob("otp"' in l:
        lines.insert(i+1, '\tdebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);\n')
        print(f'Added force_mcs file after otp at line {i+1}')
        break

with open(path, 'w') as f:
    f.writelines(lines)

print('Done')
