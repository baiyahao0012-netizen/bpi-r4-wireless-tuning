F='/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mt76-2025.01.14~8e4f72b6/mt76_connac_mcu.c'
c=open(F).read()
old='u8 mt76_force_mcs = 0xFF;'
new='u8 mt76_force_mcs = 0xFF;\nEXPORT_SYMBOL_GPL(mt76_force_mcs);'
if 'EXPORT_SYMBOL_GPL(mt76_force_mcs)' not in c:
    c=c.replace(old,new,1)
    open(F,'w').write(c)
    print('EXPORT_ADDED')
else:
    print('ALREADY')
