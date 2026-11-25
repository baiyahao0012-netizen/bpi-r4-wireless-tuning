#!/bin/bash
# Hand wlan0 to NetworkManager with a static address; remove the stale unmanaged rule.
set -x
sudo rm -f /etc/NetworkManager/conf.d/99-rtc-unmanaged-wlan0.conf
sudo nmcli connection modify rtc-media connection.interface-name wlan0
sudo nmcli connection modify rtc-media ipv4.method manual
sudo nmcli connection modify rtc-media ipv4.addresses 192.168.240.126/24
sudo nmcli connection modify rtc-media ipv4.never-default yes
sudo nmcli connection modify rtc-media connection.autoconnect yes
sudo nmcli connection modify rtc-media wifi.powersave 2
sudo nmcli connection modify netplan-wlan0-DianGroup103 connection.autoconnect no 2>/dev/null
printf 'net.ipv4.conf.all.arp_ignore=1\nnet.ipv4.conf.all.arp_announce=2\nnet.ipv4.conf.wlan0.arp_ignore=1\nnet.ipv4.conf.wlan0.arp_announce=2\n' | sudo tee /etc/sysctl.d/99-rtc-arp.conf >/dev/null
sudo sysctl --system >/dev/null 2>&1
sudo systemctl restart NetworkManager
sleep 8
nmcli -t dev | grep wlan0
ip -4 -br addr show wlan0
/sbin/iw dev wlan0 link 2>&1 | head -n 3
/sbin/iw dev wlan0 get power_save 2>&1
ping -I wlan0 -c 2 -W 2 192.168.240.1 2>&1 | tail -n 2
echo '--- AP->Pi ---'
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@192.168.240.1 'ping -c 2 -W 2 192.168.240.126 2>&1 | tail -n 2'
