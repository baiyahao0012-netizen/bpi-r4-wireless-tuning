SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== fq.h quantum field ==="
grep -n "quantum" $BP/include/net/fq.h
echo "=== fq_impl.h edits ==="
grep -n "flow->quantum" $BP/include/net/fq_impl.h
echo "=== tx.c both edits ==="
grep -n "fq_weight\|flow->quantum" $BP/net/mac80211/tx.c
echo "=== starting build ==="
cd $SDK
rm -f /root/mac80211_build.log
(make package/kernel/mac80211/compile V=s -j8 > /root/mac80211_build.log 2>&1; echo "BUILD_RC=$?" >> /root/mac80211_build.log) &
echo "build started pid=$!"
sleep 20
tail -5 /root/mac80211_build.log 2>/dev/null
echo DONE