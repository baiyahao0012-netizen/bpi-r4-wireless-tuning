#!/bin/sh
# 让板子 STA 连 PC 热点 Bai，并放行 wan zone 的 22
STA=$(uci show wireless | grep "\.mode='sta'" | head -1 | cut -d. -f2)
if [ -z "$STA" ]; then
    DEV=$(uci show wireless | grep "\.band='2g'" | head -1 | cut -d. -f2)
    [ -n "$DEV" ] || DEV=$(uci show wireless | grep "=wifi-device" | head -1 | cut -d. -f2)
    [ -n "$DEV" ] || { echo "NO_RADIO"; exit 1; }
    STA=sta0
    uci set wireless.$STA=wifi-iface
    uci set wireless.$STA.device="$DEV"
    echo "NEW_STA=$STA DEV=$DEV"
fi
echo "STA=$STA"
uci set wireless.$STA.mode='sta'
uci set wireless.$STA.ssid='Bai'
uci set wireless.$STA.key='12345678'
uci set wireless.$STA.encryption='psk2'
uci set wireless.$STA.network='wwan'
uci set wireless.$STA.disabled='0'
uci commit wireless

uci set network.wwan=interface
uci set network.wwan.proto='dhcp'
uci commit network

if ! uci show firewall | grep -q "Allow-SSH-WAN"; then
    uci add firewall rule
    uci set firewall.@rule[-1].name='Allow-SSH-WAN'
    uci set firewall.@rule[-1].src='wan'
    uci set firewall.@rule[-1].proto='tcp'
    uci set firewall.@rule[-1].dest_port='22'
    uci set firewall.@rule[-1].target='ACCEPT'
    uci commit firewall
    echo "FW_RULE_ADDED"
fi

wifi reload
/etc/init.d/firewall reload
/etc/init.d/dropbear restart
sleep 12
echo "---- iw dev ----"
iw dev 2>/dev/null | grep -E "Interface|ssid|type"
echo "---- wwan ----"
ifstatus wwan
