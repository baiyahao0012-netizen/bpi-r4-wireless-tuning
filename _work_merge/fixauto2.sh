#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
NEW=/root/kbuild/linux-6.6.73
echo "=== backup ==="
rm -rf /root/kd_gen_bak /root/kd_cfg_bak
cp -a $KD/include/generated /root/kd_gen_bak
cp -a $KD/include/config /root/kd_cfg_bak
echo "backed up"
echo "=== copy correct generated config from kbuild tree ==="
cp -a $NEW/include/generated/. $KD/include/generated/
cp -a $NEW/include/config/. $KD/include/config/
echo "=== verify autoconf.h ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_DYNAMIC_FTRACE |CONFIG_KPROBES|CONFIG_TRACEPOINTS|CONFIG_FTRACE " $KD/include/generated/autoconf.h | head
echo "=== verify auto.conf ==="
grep -E "CONFIG_FUNCTION_TRACER|CONFIG_KPROBES|CONFIG_TRACEPOINTS" $KD/include/config/auto.conf | head
echo "=== utsrelease ==="
cat $KD/include/generated/utsrelease.h
echo DONE
