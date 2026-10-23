#!/usr/bin/env python3
"""Fix connac_mcu.c: use dev->force_mcs instead of global mt76_force_mcs."""

path = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt76_connac_mcu.c'

with open(path, 'r') as f:
    lines = f.readlines()

# 1. Remove extern declaration line
for i, l in enumerate(lines):
    if 'extern u8 mt76_force_mcs;' in l:
        del lines[i]
        print(f'Removed extern line {i+1}')
        break

# 2. Replace mt76_force_mcs with dev->force_mcs in sta_tlv
for i, l in enumerate(lines):
    if 'mt76_force_mcs' in l:
        lines[i] = l.replace('mt76_force_mcs', 'dev->force_mcs')
        print(f'Replaced line {i+1}: {lines[i].strip()}')

with open(path, 'w') as f:
    f.writelines(lines)

print('Done')
