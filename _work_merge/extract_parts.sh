#!/bin/bash
BR=/root/src/openwrt-24.10.0
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
mkdir -p /root/fitparts
cd /root/fitparts
echo "=== extract parts from old FIT (p7.img) ==="
dd if=/root/p7.img of=fdt-1.dtb        bs=1 skip=$((0x561000)) count=$((0xb8f9))   2>/dev/null
dd if=/root/p7.img of=dtbo-emmc.dtbo   bs=1 skip=$((0x56d000)) count=$((0x60a))    2>/dev/null
dd if=/root/p7.img of=dtbo-rtc.dtbo    bs=1 skip=$((0x56e000)) count=$((0x11d))    2>/dev/null
dd if=/root/p7.img of=dtbo-sd.dtbo     bs=1 skip=$((0x56f000)) count=$((0x5c2))    2>/dev/null
dd if=/root/p7.img of=dtbo-wifi.dtbo   bs=1 skip=$((0x570000)) count=$((0x8f1))    2>/dev/null
dd if=/root/p7.img of=rootfs.squashfs  bs=1 skip=$((0x571000)) count=$((0xac1000)) 2>/dev/null
ls -la
echo "=== verify each is a valid blob ==="
for f in fdt-1.dtb dtbo-*.dtbo; do printf "%s: " "$f"; xxd -l 4 -p "$f"; done
printf "rootfs: "; xxd -l 4 -p rootfs.squashfs
echo "=== mkits.sh available? ==="
ls -la $BR/scripts/mkits.sh 2>&1
echo "=== mkimage available? ==="
ls -la $SDK/staging_dir/host/bin/mkimage 2>&1
$SDK/staging_dir/host/bin/mkimage -V 2>&1 | head -2
echo "=== mkimage supports which compressions ==="
$SDK/staging_dir/host/bin/mkimage -l /root/p7.img 2>&1 | head -30
echo DONE
