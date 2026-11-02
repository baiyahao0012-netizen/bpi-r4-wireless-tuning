#!/bin/bash
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-readelf
cd /root/modstage/lib/modules/6.6.73
echo "=== .gnu.linkonce.this_module sizes ==="
for m in gpio-button-hotplug.ko act_gact.ko mac80211.ko cfg80211.ko mt76.ko mt7996e.ko; do
  s=$($TC -SW $m 2>/dev/null | grep -o "this_module.*" | head -1)
  echo "$m: $s"
done
echo "=== kernel struct module size from vmlinux ==="
$TC -SW /root/kbuild/linux-6.6.73/vmlinux 2>/dev/null | grep -i "this_module" | head -2
echo DONE
