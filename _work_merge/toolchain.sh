SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== staging_dir ==="
ls $SDK/staging_dir/ 2>&1
echo "=== toolchain bin (cross gcc) ==="
ls $SDK/staging_dir/toolchain-*/bin/ 2>&1 | head -20
echo "=== kernel scripts/config ==="
ls -la $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/scripts/config 2>&1
echo "=== kernel .config exists ==="
ls -la $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config 2>&1
echo "=== mt76 build progress ==="
tail -3 /root/mt76_merge_out.log 2>&1
echo "=== mt76 make running? ==="
pgrep -c make 2>&1
echo DONE