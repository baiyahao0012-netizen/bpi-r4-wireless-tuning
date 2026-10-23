#!/usr/bin/env python3
import sys

path = '/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/debugfs.c'

with open(path, 'r') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'debugfs_create_u8("force_mcs"' in l:
        lines[i] = '\t/* disabled: debugfs_create_u8("force_mcs", 0644, dir, &mt76_force_mcs); */\n'
        print(f'line {i+1} commented out')

with open(path, 'w') as f:
    f.writelines(lines)

print('done')
