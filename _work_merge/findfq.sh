SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== find fq.h / fq_impl.h ==="
find /root/sdk $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic -maxdepth 6 -name "fq.h" -o -maxdepth 6 -name "fq_impl.h" 2>/dev/null | head -20
echo "=== pristine backports include/net ==="
ls /root/merge/pristine/backports-6.12.6/include/ 2>&1
ls /root/merge/pristine/backports-6.12.6/include/net/ 2>&1 | head -20
echo "=== backports root dirs ==="
ls $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/ 2>&1
echo "=== kernel include/net/fq.h ==="
ls -la $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/include/net/fq.h $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/include/net/fq_impl.h 2>&1
echo DONE