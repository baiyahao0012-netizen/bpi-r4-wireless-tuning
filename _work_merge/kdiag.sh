SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== .config files ==="
ls -la $KD/.config $KD/.config.before-ftrace 2>&1
echo "=== .config line count ==="
wc -l $KD/.config 2>&1
echo "=== .config head ==="
head -5 $KD/.config 2>&1
echo "=== olddefconfig log size ==="
wc -c /root/kernel_olddefconfig.log 2>&1
echo "=== retry olddefconfig manually ==="
TC=$SDK/staging_dir/toolchain-aarch64_cortex-a53_gcc-13.3.0_musl/bin/aarch64-openwrt-linux-musl-
make -C $KD ARCH=arm64 CROSS_COMPILE=$TC olddefconfig 2>&1 | tail -20
echo "make rc=$?"
echo "=== key options after ==="
grep -cE "^CONFIG_TRACING=y|^CONFIG_TRACEPOINTS=y|^CONFIG_FTRACE=y" $KD/.config 2>&1
echo DONE