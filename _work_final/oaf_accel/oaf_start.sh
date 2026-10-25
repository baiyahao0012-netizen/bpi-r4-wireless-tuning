#!/bin/sh
# Minimal OAF bring-up: kernel module + feature load + Doubao accel
[ -e /sys/module/oaf ] || insmod /root/oaf.ko
[ -x /root/oaf_load ] && /root/oaf_load /root/oaf_feature_plain.txt >/dev/null 2>&1
echo 1 > /proc/sys/fwx/appfilter_enable 2>/dev/null || true
echo 1 > /proc/sys/fwx/feature_init 2>/dev/null || true
[ -x /root/oaf_accel.sh ] && /root/oaf_accel.sh install 1900 ef >/dev/null 2>&1
