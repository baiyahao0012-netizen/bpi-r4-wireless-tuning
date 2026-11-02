echo "=== nft tables ==="; nft list tables
echo "=== oaf_bk table ==="; nft list table ip oaf_bk 2>&1 | head -20
echo "=== hostapd run files ==="; ls -la /var/run/hostapd* 2>&1 | head
echo "=== wmm in runtime conf ==="; for f in /var/run/hostapd-phy0.1.conf /var/run/hostapd-phy0.1-ap0.conf; do echo "-- $f"; grep -n "wmm_ac" $f 2>&1 | head -20; done
echo "=== md5 of modules ==="; md5sum /lib/modules/6.6.73/mt7996e.ko /lib/modules/6.6.73/mac80211.ko /lib/modules/6.6.73/mt76.ko /lib/modules/6.6.73/mt76-connac-lib.ko 2>&1
echo "=== md5 of root kos ==="; md5sum /root/*.ko 2>&1
echo "=== lsmod ==="; lsmod
echo "=== dmesg oaf ==="; dmesg 2>/dev/null | grep -iE "oaf|wdrr|edca" | tail -20
echo "=== conntrack mark 1900 ==="; grep -c "mark=1900" /proc/net/nf_conntrack 2>/dev/null; grep "mark=1900" /proc/net/nf_conntrack 2>/dev/null | head -5
echo "=== network config ==="; cat /etc/config/network
echo "=== sta0 uci ==="; uci show wireless | grep sta0
echo "=== ap info ==="; iw dev phy0.1-ap0 info
echo "=== opkg installed ==="; opkg list-installed 2>/dev/null | wc -l; opkg list-installed 2>/dev/null | grep -iE "oaf|kmod-mt|iperf|nft|f2fs" 
echo "=== hostname/ip ==="; hostname; ip -4 addr show | grep inet
echo DONE