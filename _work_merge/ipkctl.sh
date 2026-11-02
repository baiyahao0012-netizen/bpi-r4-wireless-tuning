SDK=/root/sdk/openwrt-sdk-24.10.0-mediatek-filogic_gcc-13.3.0_musl.Linux-x86_64
cd /tmp && rm -rf ipkx && mkdir ipkx && cd ipkx
tar -xzf $SDK/bin/targets/mediatek/filogic/packages/kmod-mac80211_6.6.73.6.12.6-r1_aarch64_cortex-a53.ipk
mkdir -p c && tar -xzf control.tar.gz -C c
echo "=== NEW ipk control ==="
cat c/control
echo "=== NEW ipk data ko size ==="
mkdir -p d && tar -xzf data.tar.gz -C d
ls -la d/lib/modules/6.6.73/mac80211.ko
echo "=== strings in ipk ko ==="
strings -a d/lib/modules/6.6.73/mac80211.ko | grep -c "wifi_dscp"
strings -a d/lib/modules/6.6.73/mac80211.ko | grep -c "__tracepoint"
echo "=== relay kmod built? ==="
ls $SDK/bin/targets/mediatek/filogic/packages/ | grep -i "relay" | head
echo DONE