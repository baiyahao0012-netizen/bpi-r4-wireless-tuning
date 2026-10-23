#!/usr/bin/env python3
"""Revert to global variable + custom fops approach.
No mt76.h struct change, mt7996e.ko stays original."""

base = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/'

# 1. Revert mt76.h: remove force_mcs field
h_path = base + 'mt76.h'
with open(h_path, 'r') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if 'force_mcs' in l and 'MCS force lock' in l:
        del lines[i]
        print(f'mt76.h: removed force_mcs field at line {i+1}')
        break
with open(h_path, 'w') as f:
    f.writelines(lines)

# 2. Revert debugfs.c: remove &dev->force_mcs, add global var + custom fops
db_path = base + 'debugfs.c'
with open(db_path, 'r') as f:
    lines = f.readlines()

# Remove the debugfs_create_u8 force_mcs line
for i, l in enumerate(lines):
    if 'debugfs_create_u8("force_mcs"' in l and 'dev->force_mcs' in l:
        del lines[i]
        print(f'debugfs.c: removed old force_mcs line at {i+1}')
        break

# Insert global var + fops after #include "mt76.h"
for i, l in enumerate(lines):
    if '#include "mt76.h"' in l:
        insert = '''
/* MCS force lock: 0-7 = force MCS, 0xFF = auto */
u8 mt76_force_mcs = 0xFF;
EXPORT_SYMBOL_GPL(mt76_force_mcs);

static int force_mcs_show(struct seq_file *s, void *data)
{
	seq_printf(s, "%u\\n", mt76_force_mcs);
	return 0;
}

static ssize_t force_mcs_write(struct file *file, const char __user *userbuf,
			       size_t count, loff_t *pos)
{
	char buf[16];
	unsigned long val;
	if (count >= sizeof(buf))
		return -EINVAL;
	if (copy_from_user(buf, userbuf, count))
		return -EFAULT;
	buf[count] = '\\0';
	val = simple_strtoul(buf, NULL, 0);
	if (val > 0xFF)
		return -EINVAL;
	mt76_force_mcs = (u8)val;
	return count;
}

DEFINE_DEBUGFS_ATTRIBUTE(force_mcs_fops, force_mcs_show, force_mcs_write, "%u\\n");
'''
        lines.insert(i+1, insert)
        print(f'debugfs.c: inserted global var + fops after line {i+1}')
        break

# Add debugfs_create_file after otp blob
for i, l in enumerate(lines):
    if 'debugfs_create_blob("otp"' in l:
        lines.insert(i+1, '\tdebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);\n')
        print(f'debugfs.c: added force_mcs file after otp at line {i+1}')
        break

with open(db_path, 'w') as f:
    f.writelines(lines)

# 3. Revert connac_mcu.c: extern global var, use mt76_force_mcs
cu_path = base + 'mt76_connac_mcu.c'
with open(cu_path, 'r') as f:
    lines = f.readlines()

# Add extern declaration after includes
for i, l in enumerate(lines):
    if '#include "mt76.h"' in l or '#include "mt76_connac.h"' in l:
        continue
    if l.startswith('#include'):
        continue
    # First non-include line, insert extern before it
    lines.insert(i, '/* MCS force lock */\nextern u8 mt76_force_mcs;\n\n')
    print(f'connac_mcu.c: added extern at line {i+1}')
    break

# Replace dev->force_mcs with mt76_force_mcs
for i, l in enumerate(lines):
    if 'dev->force_mcs' in l:
        lines[i] = l.replace('dev->force_mcs', 'mt76_force_mcs')
        print(f'connac_mcu.c: replaced line {i+1}')

with open(cu_path, 'w') as f:
    f.writelines(lines)

print('All done')
