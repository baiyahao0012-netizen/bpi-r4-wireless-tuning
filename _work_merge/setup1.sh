set -e
SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
SUBSYS=$SDK/package/kernel/mac80211/patches/subsys
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== fq.h location in backports ==="
ls -la $BP/include/net/fq.h $BP/include/net/fq_impl.h 2>&1
echo "=== copy patches ==="
cp "/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src/354-wifi-mac80211-add-dscp-latency-tracepoint.patch" $SUBSYS/
cp "/mnt/d/Desktop/AI 辅助对话/_build/001-wdrr.patch" $SUBSYS/360-wdrr-private-scheduler.patch
ls -la $SUBSYS/ | tail -5
echo "=== enable MAC80211_TRACING ==="
cp $SDK/.config $SDK/.config.bak-before-merge
sed -i "s|^# CONFIG_PACKAGE_MAC80211_TRACING is not set|CONFIG_PACKAGE_MAC80211_TRACING=y|" $SDK/.config
grep -n "MAC80211_TRACING" $SDK/.config
echo "=== clean ==="
cd $SDK
make package/kernel/mac80211/clean V=s > /root/mac80211_clean.log 2>&1 && echo CLEAN_OK || (echo CLEAN_FAIL; tail -20 /root/mac80211_clean.log)
echo "=== prepare (applies all patches) ==="
make package/kernel/mac80211/prepare V=s > /root/mac80211_prepare.log 2>&1 && echo PREPARE_OK || (echo PREPARE_FAIL; tail -40 /root/mac80211_prepare.log)
echo "=== verify patched ==="
grep -c "fq_weight" $BP/net/mac80211/tx.c 2>/dev/null || echo "WDRR tx.c: 0"
grep -c "wifi_dscp" $BP/net/mac80211/trace.h 2>/dev/null || echo "DSCP trace.h: 0"
grep -c "wifi_dscp" $BP/net/mac80211/status.c 2>/dev/null || echo "DSCP status.c: 0"
grep -c "wifi_dscp" $BP/net/mac80211/rx.c 2>/dev/null || echo "DSCP rx.c: 0"
grep -c "wifi_dscp" $BP/net/mac80211/ieee80211_i.h 2>/dev/null || echo "DSCP i.h: 0"
echo DONE