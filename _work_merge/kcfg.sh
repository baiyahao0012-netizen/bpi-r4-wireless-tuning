echo "=== backports Kconfig: MAC80211_TRACING ==="
grep -n -B3 -A8 "config MAC80211_TRACING" /root/merge/pristine/backports-6.12.6/net/mac80211/Kconfig 2>&1
echo "=== backports Makefile: trace.o ==="
grep -n "trace" /root/merge/pristine/backports-6.12.6/net/mac80211/Makefile 2>&1
echo "=== kernel Kconfig TRACEPOINTS/EVENT_TRACING ==="
grep -n -A6 "^config TRACEPOINTS\|^config EVENT_TRACING\|^config TRACING$" /root/merge/pristine/backports-6.12.6/../backports-6.12.6/Kconfig 2>/dev/null | head -20
echo "=== SDK kernel config: EVENT_TRACING / TRACEPOINTS ==="
K=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/linux-6.6.73/.config
grep -cE "^CONFIG_EVENT_TRACING|^CONFIG_TRACEPOINTS|^CONFIG_TRACING=" $K
grep -nE "EVENT_TRACING|TRACEPOINTS" $K | head
echo DONE