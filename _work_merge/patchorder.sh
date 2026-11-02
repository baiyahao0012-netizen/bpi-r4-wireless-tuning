BR=/root/src/openwrt-24.10.0
echo "=== Kernel/Patch definition ==="
grep -n -A40 "define Kernel/Patch/Default" $BR/include/kernel-defaults.mk 2>&1 | head -60
echo "=== PATCHES file in generic ==="
cat $BR/target/linux/generic/PATCHES 2>&1
echo "=== patch dirs variables ==="
grep -n "GENERIC_PATCH_DIRS\|PLATFORM_PATCH_DIRS\|KERNEL_PATCHVER" $BR/include/kernel.mk 2>&1 | head -20
echo "=== download progress ==="
cat /root/dl_kernel.log 2>&1 | tail -5
echo DONE