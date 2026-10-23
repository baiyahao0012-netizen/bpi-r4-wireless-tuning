F='/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/debugfs.c'
lines=open(F).readlines()
if lines[0].startswith('extern u8'):
    lines=lines[1:]
for i,l in enumerate(lines):
    if '#include "mt76.h"' in l:
        lines.insert(i+1,'extern u8 mt76_force_mcs;\n')
        break
open(F,'w').writelines(lines)
print('FIXED')
