echo "=== mt76 merge build result ==="
cat /root/mt76_merge_out.log 2>&1 | tail -30
echo "=== mt76 errors ==="
grep -nE "error:|Error [0-9]" /tmp/mt76_build_merge.log 2>/dev/null | grep -v ignored | head -15
echo "=== still running? ==="
pgrep -c make 2>&1
echo "=== SDK config: KERNEL_FTRACE block ==="
grep -n -A14 "^config KERNEL_FTRACE" /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/config/Config-kernel.in 2>&1 | head -25
echo "=== target/linux makefile support ==="
ls /root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/target/linux/Makefile 2>&1
echo DONE