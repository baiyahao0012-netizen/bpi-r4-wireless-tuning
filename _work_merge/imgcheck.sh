SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== SDK bin/targets ==="
ls -la $SDK/bin/targets/mediatek/filogic/ 2>&1 | head -20
echo "=== SDK target/linux/mediatek ==="
ls $SDK/target/linux/mediatek/ 2>&1 | head
echo "=== SDK .config target/image opts ==="
grep -nE "^CONFIG_TARGET_|^CONFIG_KERNEL_(FTRACE|ENABLE_DEFAULT_TRACERS|TRACEPOINTS)|^CONFIG_TARGET_ROOTFS" $SDK/.config | head -20
echo "=== buildroot src exists? ==="
ls /root/src/openwrt-24.10.0/ 2>&1 | head -15
echo "=== buildroot .config? ==="
ls -la /root/src/openwrt-24.10.0/.config 2>&1
echo "=== feeds ==="
ls /root/src/openwrt-24.10.0/feeds/ 2>&1 | head
echo "=== toolchain built in buildroot? ==="
ls -d /root/src/openwrt-24.10.0/staging_dir 2>&1
echo DONE