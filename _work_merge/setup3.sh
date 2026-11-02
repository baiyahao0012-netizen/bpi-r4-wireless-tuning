SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== dry-run on pristine (correct cwd) ==="
cd /root/merge/pristine/backports-6.12.6
patch -p1 --dry-run < /root/merge/wdrr-gen/360-wdrr-private-scheduler.patch 2>&1 | head -20
echo "=== clean + prepare ==="
cd $SDK
make package/kernel/mac80211/clean V=s > /root/mac80211_clean.log 2>&1; echo "clean rc=$?"
make package/kernel/mac80211/prepare V=s > /root/mac80211_prepare.log 2>&1; echo "prepare rc=$?"
grep -nE "Patch failed|malformed|Error" /root/mac80211_prepare.log | head -10
tail -6 /root/mac80211_prepare.log
BP=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6
echo "=== verify ==="
for f in net/mac80211/tx.c net/mac80211/trace.h net/mac80211/status.c net/mac80211/rx.c net/mac80211/ieee80211_i.h include/net/fq.h include/net/fq_impl.h; do printf "%-32s " "$f"; printf "dscp=%s wdrr=%s\n" "$(grep -c wifi_dscp $BP/$f 2>/dev/null)" "$(grep -c -e fq_weight -e "flow->quantum" $BP/$f 2>/dev/null)"; done
echo "=== tracepoint present in trace.h? ==="
grep -n "TRACE_EVENT(wifi_dscp" $BP/net/mac80211/trace.h
echo DONE