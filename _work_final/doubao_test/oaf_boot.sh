#!/bin/sh
# Load OAF + EDCA tuning at boot (WiFi needs time to come up)
sleep 20
insmod /root/oaf.ko 2>/dev/null
/root/oaf_load /root/oaf_feature_plain.txt >/dev/null 2>&1
echo 1 > /proc/sys/fwx/appfilter_enable 2>/dev/null
echo 1 > /proc/sys/fwx/feature_init 2>/dev/null
/root/edca_set phy0.1-ap0 3 1 3 7 94 >/dev/null 2>&1
/root/edca_set phy0.1-ap0 0 3 31 1023 0 >/dev/null 2>&1
/root/edca_set phy0.1-ap0 2 2 7 15 94 >/dev/null 2>&1
