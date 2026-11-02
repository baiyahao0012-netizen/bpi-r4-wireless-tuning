SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
KO=$SDK/build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/mac80211-regular/backports-6.12.6/net/mac80211/mac80211.ko
ls -la "$KO"
echo "--- md5 ---"; md5sum "$KO"
echo "--- vermagic ---"; strings "$KO" | grep -m1 vermagic
echo "--- fq_weight ---"; strings "$KO" | grep -m2 fq_weight
echo "--- wifi_dscp ---"; strings "$KO" | grep -m3 wifi_dscp
echo "--- WDRR marker ---"; strings "$KO" | grep -m1 "private WDRR"
echo "--- build rc ---"; grep BUILD_RC= /root/mac80211_build.log || echo NONE
echo DONE