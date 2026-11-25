#!/bin/bash
# Connect the (renamed) USB adapter to BPI-R4-5G via wpa_supplicant.
IF=${IF:-wlan0}
sudo pkill -x wpa_supplicant 2>/dev/null
sleep 1
sudo ip link set "$IF" up
wpa_passphrase BPI-R4-5G 12345678 | sudo tee /etc/wpa_supplicant/wpa0.conf >/dev/null
sudo wpa_supplicant -B -i "$IF" -c /etc/wpa_supplicant/wpa0.conf 2>&1 | tail -n 1
sleep 6
sudo ip addr add 192.168.240.126/24 dev "$IF" 2>/dev/null
sudo iw dev "$IF" set power_save off
/sbin/iw dev "$IF" link 2>&1 | head -n 4
ip -4 -br addr show "$IF"
ping -I "$IF" -c 2 -W 2 192.168.240.1 2>&1 | tail -n 2

