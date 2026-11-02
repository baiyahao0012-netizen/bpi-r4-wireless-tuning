echo "=== uname ==="; uname -a
echo "=== release ==="; cat /etc/openwrt_release
echo "=== cmdline ==="; cat /proc/cmdline
echo "=== mounts ==="; mount | head -30
echo "=== block ==="; ls -la /dev/fit* 2>/dev/null; cat /proc/partitions
echo "=== modules ==="; ls /lib/modules/
echo "=== lsmod (filtered) ==="; lsmod | grep -E "oaf|mac80211|mt7996|mt76|cfg80211"
echo "=== /root listing ==="; ls -la /root | head -60
echo "=== /root/oaf* ==="; ls -la /root/oaf* 2>/dev/null
echo "=== nft ==="; nft list ruleset 2>/dev/null | head -60
echo "=== hostapd runtime bk ==="; grep -n "wmm_ac" /var/run/hostapd-phy0.1.conf 2>/dev/null | head -40
echo "=== iw dev ==="; iw dev | head -40
echo "=== wireless uci summary ==="; uci show wireless 2>/dev/null | head -60
echo "=== overlay/rootfs_data ==="; ls -la /overlay 2>/dev/null | head; df -h | head -20
echo DONE