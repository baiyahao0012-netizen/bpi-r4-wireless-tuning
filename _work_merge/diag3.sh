SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KD=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73
echo "=== kernel dir top level ==="
ls $KD/ 2>&1 | tr "\n" " "
echo
echo "=== Kconfig/Kbuild ==="
ls -la $KD/Kconfig $KD/Kbuild 2>&1
echo "=== dl dir ==="
ls $SDK/dl/ 2>&1 | head -30
echo "=== buildroot generic ==="
ls /root/src/openwrt-24.10.0/target/linux/generic/ 2>&1 | head -20
echo "=== git version ==="
git --version 2>&1
echo "=== gh cli ==="
which gh 2>&1; gh --version 2>&1 | head -2
echo "=== git config ==="
git config --global --list 2>&1 | head -20
echo "=== ssh keys ==="
ls -la /root/.ssh/ 2>&1
echo "=== windows git ==="
ls "/mnt/c/Program Files/Git/cmd/git.exe" 2>&1
echo DONE