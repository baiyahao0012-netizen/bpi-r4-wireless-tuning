#!/usr/bin/env python3
# Fix the broken patch in mt76_connac_mcu.c

import re

filepath = "build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt76_connac_mcu.c"

with open(filepath, 'r') as f:
    lines = f.readlines()

# First, remove the broken patch (the if (mt76_force_mcs...) block that's in the middle of memcpy)
new_lines = []
skip = False
for i, line in enumerate(lines):
    if 'if (mt76_force_mcs < 8) {' in line:
        skip = True
        continue
    if skip and '}' in line:
        skip = False
        continue
    if skip:
        continue
    new_lines.append(line)

# Now find the end of memcpy (the line with HT_MCS_MASK_NUM);)
for i, line in enumerate(new_lines):
    if 'HT_MCS_MASK_NUM);' in line and 'rx_mcs_bitmask' in new_lines[i-2]:
        # Insert our patch after this line
        patch = '\n\tif (mt76_force_mcs < 8) {\n\t\tmemset(ra_info->rx_mcs_bitmask, 0, HT_MCS_MASK_NUM);\n\t\tra_info->rx_mcs_bitmask[mt76_force_mcs] = 0xff;\n\t\tprintk("mt76: FORCE MCS%u\\n", mt76_force_mcs);\n\t}\n'
        new_lines.insert(i+1, patch)
        print(f'Fixed! Inserted patch after line {i+1}')
        break

with open(filepath, 'w') as f:
    f.writelines(new_lines)

print('Done!')
