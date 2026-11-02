SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== current .config value ==="
grep -n "MAC80211_TRACING\|PACKAGE_KERNEL_RELAY\|MAC80211_DEBUGFS" $SDK/.config
echo "=== mac80211 Makefile config block ==="
grep -n -B2 -A10 "PACKAGE_MAC80211_TRACING" $SDK/package/kernel/mac80211/Makefile
echo "=== how CPTCFG_MAC80211_TRACING is set ==="
grep -n -B3 -A8 "MAC80211_TRACING" $SDK/package/kernel/mac80211/Makefile | head -40
echo "=== tmp/.config-package.in symbol ==="
grep -n -A6 "config PACKAGE_MAC80211_TRACING" $SDK/tmp/.config-package.in 2>/dev/null | head -20
echo "=== config diff vs backup ==="
diff $SDK/.config.bak-before-merge $SDK/.config | head -20
echo DONE