SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
echo "=== mac80211 package ==="
ls -la $SDK/package/kernel/mac80211/
echo "--- Makefile head ---"
head -30 $SDK/package/kernel/mac80211/Makefile
echo "=== patches dirs ==="
ls $SDK/package/kernel/mac80211/patches/
ls $SDK/package/kernel/mac80211/patches/build/ | head -5
echo "build patches: $(ls $SDK/package/kernel/mac80211/patches/build/ | wc -l)"
echo "subsys patches: $(ls $SDK/package/kernel/mac80211/patches/subsys/ | wc -l)"
ls $SDK/package/kernel/mac80211/patches/subsys/ | tail -10
echo "=== SDK .config ==="
ls -la $SDK/.config 2>&1
grep -nE "MAC80211|CFG80211" $SDK/.config 2>/dev/null | head -20
echo "=== SDK target config ==="
ls $SDK/target/linux/mediatek/filogic/ 2>/dev/null | head
echo "=== mt76 package ==="
ls $SDK/package/kernel/mt76/
ls $SDK/package/kernel/mt76/patches/ 2>/dev/null | head
echo DONE