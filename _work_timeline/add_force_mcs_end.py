#!/usr/bin/env python3
"""Find end of struct mt76_dev and add force_mcs at the end."""

path = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt76.h'

with open(path, 'r') as f:
    lines = f.readlines()

# Find struct mt76_dev {
start = None
for i, l in enumerate(lines):
    if 'struct mt76_dev {' in l:
        start = i
        print(f'start at line {i+1}')
        break

# Find matching }
depth = 0
end = None
for i in range(start, len(lines)):
    if '{' in lines[i]:
        depth += lines[i].count('{')
    if '}' in lines[i]:
        depth -= lines[i].count('}')
    if depth == 0:
        end = i
        print(f'end at line {i+1}: {lines[i].strip()}')
        break

# Add force_mcs before the closing }
insert_line = end  # the line with };
lines.insert(insert_line, '\tu8 force_mcs;\t/* MCS force lock: 0-7 = force MCS, 0xFF = auto */\n')
print(f'inserted at line {insert_line+1}')

with open(path, 'w') as f:
    f.writelines(lines)

print('Done')
