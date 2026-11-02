SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== kernel build dir ==="
ls $KD/ 2>&1 | head -20
echo "=== vmlinux / Image ==="
ls -la $KD/vmlinux $KD/arch/arm64/boot/Image 2>&1
echo "=== BPI-R4 in filogic image makefile ==="
grep -n -B3 -A25 "bpi-r4" $SDK/target/linux/mediatek/image/filogic.mk 2>&1 | head -60
echo "=== its files ==="
ls $SDK/target/linux/mediatek/image/ 2>&1
echo DONE