SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
SUBSYS=$SDK/package/kernel/mac80211/patches/subsys
echo "=== current backports tree state ==="
ls -la $BP 2>&1 | head -10
find $BP -maxdepth 1 2>/dev/null | wc -l
echo "=== pristine has include/net/fq.h ? ==="
ls -la /root/merge/pristine/backports-6.12.6/include/net/fq.h
echo "=== copy patches ==="
cp "/mnt/d/Desktop/AI 辅助对话/_work_merge/other_src/354-wifi-mac80211-add-dscp-latency-tracepoint.patch" $SUBSYS/ && echo COPIED_354
cp "/mnt/d/Desktop/AI 辅助对话/_build/001-wdrr.patch" $SUBSYS/360-wdrr-private-scheduler.patch && echo COPIED_WDRR
ls $SUBSYS/ | tail -4
echo "=== enable MAC80211_TRACING ==="
[ -f $SDK/.config.bak-before-merge ] || cp $SDK/.config $SDK/.config.bak-before-merge
sed -i "s|^# CONFIG_PACKAGE_MAC80211_TRACING is not set|CONFIG_PACKAGE_MAC80211_TRACING=y|" $SDK/.config
grep -n "MAC80211_TRACING" $SDK/.config
echo "=== clean ==="
cd $SDK && make package/kernel/mac80211/clean V=s > /root/mac80211_clean.log 2>&1; echo "clean rc=$?"
echo "=== prepare ==="
make package/kernel/mac80211/prepare V=s > /root/mac80211_prepare.log 2>&1; echo "prepare rc=$?"
tail -20 /root/mac80211_prepare.log
echo "=== verify patched files ==="
for f in net/mac80211/tx.c net/mac80211/trace.h net/mac80211/status.c net/mac80211/rx.c net/mac80211/ieee80211_i.h include/net/fq.h include/net/fq_impl.h; do printf "%-32s " "$f"; if [ -f "$BP/$f" ]; then printf "dscp=%s wdrr=%s\n" "$(grep -c wifi_dscp $BP/$f)" "$(grep -c -e fq_weight -e quantum $BP/$f)"; else echo MISSING; fi; done
echo DONE