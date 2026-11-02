SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== current mac80211-regular tree: WDRR? DSCP? ==="
grep -c "fq_weight" $BP/net/mac80211/tx.c 2>/dev/null || echo "tx.c fq_weight: 0"
grep -c "wifi_dscp" $BP/net/mac80211/trace.h 2>/dev/null || echo "trace.h wifi_dscp: 0"
echo "=== other variants ==="
ls $SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-smallbuffers/
echo "=== pristine backports tarball ==="
ls -la $SDK/dl/backports-6.12.6.tar.xz
mkdir -p /root/merge/pristine && cd /root/merge/pristine
rm -rf backports-6.12.6
tar -xf $SDK/dl/backports-6.12.6.tar.xz 2>&1 | head -3
ls -d /root/merge/pristine/* | head
echo "=== pristine has wifi_dscp? (should be 0) ==="
grep -rc "wifi_dscp" /root/merge/pristine/backports-6.12.6/net/mac80211/ 2>/dev/null | grep -v ":0" | head
echo "=== pristine version ==="
cat /root/merge/pristine/backports-6.12.6/versions 2>/dev/null | head -5
echo DONE