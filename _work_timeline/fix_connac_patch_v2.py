#!/usr/bin/env python3
# Correctly patch mt76_connac_mcu.c - insert AFTER memcpy ends

filepath = "build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt76_connac_mcu.c"

with open(filepath, 'r') as f:
    lines = f.readlines()

# Add extern after last include
for i, line in enumerate(lines):
    if line.startswith('#include') and i > 10:
        # Find the last include block
        continue
    if i > 5 and lines[i-1].startswith('#include') and not line.startswith('#include'):
        lines.insert(i, 'extern u8 mt76_force_mcs;\n')
        print(f'Added extern after line {i}')
        break

# Find memcpy end: line with HT_MCS_MASK_NUM);
for i, line in enumerate(lines):
    if 'HT_MCS_MASK_NUM);' in line and i > 900:
        # Insert patch after this line
        patch = '\n\tif (mt76_force_mcs < 8) {\n\t\tmemset(ra_info->rx_mcs_bitmask, 0, HT_MCS_MASK_NUM);\n\t\tra_info->rx_mcs_bitmask[mt76_force_mcs] = 0xff;\n\t\tprintk("mt76: FORCE MCS%u\\n", mt76_force_mcs);\n\t}\n'
        lines.insert(i+1, patch)
        print(f'Inserted patch after line {i+1}')
        break

with open(filepath, 'w') as f:
    f.writelines(lines)

print('Done!')
