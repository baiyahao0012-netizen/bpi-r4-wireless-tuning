SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== full listing of kernel dir ==="
ls -a $KD/ 2>&1
echo "=== Kconfig? ==="
ls -la $KD/Kconfig $KD/Kbuild 2>&1
echo "=== dl dir linux tarballs ==="
ls $SDK/dl/ 2>&1 | head -40
echo "=== any linux-6.6 tarball anywhere ==="
find / -maxdepth 6 -name "linux-6.6*.tar*" 2>/dev/null | head
echo "=== buildroot target/linux/generic ==="
ls /root/src/openwrt-24.10.0/target/linux/generic/ 2>&1 | head -20
echo "=== buildroot mediatek ==="
ls /root/src/openwrt-24.10.0/target/linux/mediatek/ 2>&1
echo "=== buildroot config-6.6 files ==="
ls /root/src/openwrt-24.10.0/target/linux/mediatek/filogic/ 2>&1 | head
echo DONE