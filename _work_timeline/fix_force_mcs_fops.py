#!/usr/bin/env python3
"""Fix debugfs force_mcs node: use custom fops instead of debugfs_create_u8."""

path = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/debugfs.c'

with open(path, 'r') as f:
    content = f.read()

# 1. Add force_mcs show/write functions after the EXPORT_SYMBOL line
old_export = 'EXPORT_SYMBOL_GPL(mt76_force_mcs);\n'
new_export = '''EXPORT_SYMBOL_GPL(mt76_force_mcs);

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

if old_export in content:
    content = content.replace(old_export, new_export, 1)
    print('Added force_mcs fops functions')
else:
    print('ERROR: export line not found')
    exit(1)

# 2. Replace the commented-out debugfs_create_u8 line with debugfs_create_file
old_line = '//\tdebugfs_create_u8("force_mcs", 0644, dir, &mt76_force_mcs);'
new_line = '\tdebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);'

if old_line in content:
    content = content.replace(old_line, new_line, 1)
    print('Replaced debugfs_create_u8 with debugfs_create_file')
else:
    # Try alternative: maybe it's /* ... */ commented
    if 'debugfs_create_u8("force_mcs"' in content:
        # Find the line and replace it
        lines = content.split('\\n')
        for i, l in enumerate(lines):
            if 'debugfs_create_u8("force_mcs"' in l:
                lines[i] = '\\tdebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);'
                print(f'Replaced line {i+1}')
                break
        content = '\\n'.join(lines)
    else:
        print('WARNING: force_mcs debugfs line not found, adding it manually')
        # Add after debugfs_create_blob("otp", ...)
        otp_line = 'debugfs_create_blob("otp", 0400, dir, &dev->otp);'
        if otp_line in content:
            content = content.replace(otp_line, otp_line + '\\n\\tdebugfs_create_file("force_mcs", 0644, dir, NULL, &force_mcs_fops);', 1)
            print('Added force_mcs debugfs file after otp blob')

with open(path, 'w') as f:
    f.write(content)

print('Done')
