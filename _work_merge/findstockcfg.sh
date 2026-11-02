#!/bin/bash
echo "=== buildroot kernel config? ==="
ls -la /root/src/openwrt-24.10.0/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config 2>&1
ls -la /root/src/openwrt-24.10.0/.config 2>&1
echo "=== buildroot build_dir ==="
ls /root/src/openwrt-24.10.0/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/ 2>&1 | head
echo "=== search for any saved kernel configs ==="
find /root -maxdepth 4 -name ".config" -path "*linux*" 2>/dev/null | head
ls -la /root/config* 2>/dev/null
echo "=== target config fragments ==="
ls /root/src/openwrt-24.10.0/target/linux/mediatek/filogic/ 2>/dev/null | head
echo DONE
